# -*- coding: utf-8 -*-
import time, traceback
import numpy as np
import psutil
from multiprocessing import get_context
from PyQt5.QtCore import QThread, pyqtSignal

from .helpers import ACORConfig

class ACOROptimizer:
    """Implementa el algoritmo de optimizaci0n ACOR multi-colonia."""
    def __init__(self, fitness_func, bounds, config: ACORConfig, warm_start_params=None):
        self.fitness = fitness_func
        self.bounds = bounds
        self.config = config
        self.warm_start_params = warm_start_params
        
        self.DIM = bounds.shape[0]
        self.LOW = bounds[:, 0]
        self.HIGH = bounds[:, 1]
        self.RANGE = self.HIGH - self.LOW
        
        self.best_params_global = None
        self.best_cost_global = float("inf")
        self.history_best_cost = []
        self.history_best_params = []
        
        self.progress_callback = None
        self._stop_requested = False
        self.archives = []
        self.colony_costs = []

    def __getstate__(self):
        # Permite que la clase sea "picklable" para multiprocessing
        s = self.__dict__.copy()
        s["progress_callback"] = None
        s["fitness"] = None
        return s

    def clear_stop(self): self._stop_requested = False
    def request_stop(self): self._stop_requested = True
    def should_stop(self): return self._stop_requested
    def _get_opposite_solution(self, solution): return self.LOW + self.HIGH - solution

    def optimize(self, tmax_seconds=None, plateau_K=None):
        self.clear_stop()
        self.history_best_cost.clear()
        self.history_best_params.clear()
        start_time = time.time()
        cfg = self.config
        n_workers = max(1, int(psutil.cpu_count(logical=True) * 0.8))
        ctx = get_context("spawn")

        with ctx.Pool(n_workers) as pool:
            self._initialize_colonies(pool)
            no_improve_global = 0

            for it in range(1, cfg.max_iter + 1):
                if self._check_stop_conditions(it, start_time, tmax_seconds, no_improve_global, plateau_K): break

                for c in range(cfg.colonies_count):
                    archive, costs = self.archives[c], self.colony_costs[c]
                    lam = cfg.archive_size / 2
                    P = np.exp(-np.arange(cfg.archive_size) / lam)
                    P /= P.sum()
                    
                    new_sols = self._generate_solutions(archive, P)
                    new_costs = np.array(pool.map(self.fitness, new_sols))

                    combined = np.vstack((archive, new_sols))
                    comb_costs = np.hstack((costs, new_costs))
                    elite_idx = np.argsort(comb_costs)[:cfg.archive_size]
                    self.archives[c], self.colony_costs[c] = combined[elite_idx], comb_costs[elite_idx]

                    if cfg.local_search_enabled and it % cfg.local_search_frequency == 0:
                        self.archives[c], self.colony_costs[c] = self._apply_local_search(self.archives[c], self.colony_costs[c], pool)

                if it % cfg.migration_interval == 0:
                    self._apply_migration()

                if cfg.refinement_enabled and it % cfg.refinement_frequency == 0:
                    self._apply_greedy_refinement(pool, it)

                current_best_cost_global = min(colony_costs[0] for colony_costs in self.colony_costs)
                if current_best_cost_global + 1e-12 < self.best_cost_global:
                    self.best_cost_global = current_best_cost_global
                    no_improve_global = 0
                    for c in range(cfg.colonies_count):
                        if self.colony_costs[c][0] == self.best_cost_global:
                            self.best_params_global = self.archives[c][0].copy()
                            break
                else:
                    no_improve_global += 1

                self.history_best_cost.append(self.best_cost_global)
                self.history_best_params.append(self.best_params_global.copy())

                if self.progress_callback:
                    prog = int(it * 100 / cfg.max_iter)
                    msg = f"Iter {it}/{cfg.max_iter} — Best Cost: {self.best_cost_global:.3e} (Global Plateau: {no_improve_global})"
                    self.progress_callback(prog, msg, self.best_params_global if (it % 10 == 0) else None)

        return self.best_params_global, self.best_cost_global

    def _initialize_colonies(self, pool):
        cfg = self.config
        self.archives = []
        self.colony_costs = []
        for i in range(cfg.colonies_count):
            base_size = cfg.archive_size
            if cfg.obl_enabled:
                half_size = (base_size + 1) // 2
                initial_sols = np.random.uniform(self.LOW, self.HIGH, size=(half_size, self.DIM))
                opposite_sols = self._get_opposite_solution(initial_sols)
                if i == 0 and self.warm_start_params is not None:
                    initial_sols[0] = self.warm_start_params.copy()
                    opposite_sols[0] = self._get_opposite_solution(initial_sols[0])
                combined_sols = np.vstack((initial_sols, opposite_sols))
                costs = np.array(pool.map(self.fitness, combined_sols))
                best_indices = np.argsort(costs)[:base_size]
                archive = combined_sols[best_indices]
            else:
                archive = np.random.uniform(self.LOW, self.HIGH, size=(base_size, self.DIM))
                if i == 0 and self.warm_start_params is not None: archive[0] = self.warm_start_params.copy()
            
            costs = np.array(pool.map(self.fitness, archive))
            idx = np.argsort(costs)
            self.archives.append(archive[idx])
            self.colony_costs.append(costs[idx])
        
        self.best_cost_global = self.colony_costs[0][0]
        self.best_params_global = self.archives[0][0].copy()

    def _apply_migration(self):
        cfg = self.config
        if cfg.colonies_count <= 1: return
        for i in range(cfg.colonies_count):
            source_colony_idx = i
            target_colony_idx = (i + 1) % cfg.colonies_count
            
            migrants = self.archives[source_colony_idx][:cfg.migration_size]
            target_archive = self.archives[target_colony_idx]
            target_costs = self.colony_costs[target_colony_idx]
            
            target_archive[-cfg.migration_size:] = migrants
            migrant_costs = self.colony_costs[source_colony_idx][:cfg.migration_size]
            target_costs[-cfg.migration_size:] = migrant_costs
            
            idx = np.argsort(target_costs)
            self.archives[target_colony_idx] = target_archive[idx]
            self.colony_costs[target_colony_idx] = target_costs[idx]

    def _check_stop_conditions(self, it, start_time, tmax_seconds, no_improve, plateau_K):
        if self.should_stop():
            if self.progress_callback: self.progress_callback(int(it*100/self.config.max_iter), "Detenido.", None)
            return True
        if tmax_seconds is not None and (time.time() - start_time) >= tmax_seconds:
            if self.progress_callback: self.progress_callback(int(it*100/self.config.max_iter), "L0mite de tiempo.", None)
            return True
        if plateau_K is not None and no_improve >= int(plateau_K):
            if self.progress_callback: self.progress_callback(int(it*100/self.config.max_iter), f"Plateau global (K={plateau_K}).", None)
            return True
        return False

    def _generate_solutions(self, archive, P):
        cfg = self.config
        new_sols = np.zeros((cfg.n_ants, self.DIM))
        for k in range(cfg.n_ants):
            i_sel = np.random.choice(cfg.archive_size, p=P)
            mu = archive[i_sel]
            sigma = cfg.q * (np.abs(archive - mu).sum(axis=0) / (cfg.archive_size - 1) + 1e-12)
            sol = np.random.normal(mu, sigma)
            new_sols[k] = np.clip(sol, self.LOW, self.HIGH)
        return new_sols

    def _apply_local_search(self, archive, costs, pool):
        best_params = archive[0].copy()
        radius = self.config.local_search_radius
        n_points = self.config.local_search_points
        perturbations = np.random.normal(0, radius * self.RANGE, size=(n_points, self.DIM))
        candidates = np.clip(best_params + perturbations, self.LOW, self.HIGH)
        candidate_costs = np.array(pool.map(self.fitness, candidates))
        best_local_idx = np.argmin(candidate_costs)
        if candidate_costs[best_local_idx] < costs[0]:
            archive[0], costs[0] = candidates[best_local_idx], candidate_costs[best_local_idx]
            idx = np.argsort(costs)
            archive, costs = archive[idx], costs[idx]
        return archive, costs

    def _apply_greedy_refinement(self, pool, it):
        if self.progress_callback: self.progress_callback(int(it*100/self.config.max_iter), "Aplicando pulido codicioso...", None)
        best_sol = self.best_params_global.copy()
        best_cost = self.best_cost_global
        candidates = []
        step_sizes = self.RANGE * self.config.refinement_step
        for i in range(self.DIM):
            p_plus = best_sol.copy()
            p_plus[i] = min(p_plus[i] + step_sizes[i], self.HIGH[i])
            candidates.append(p_plus)
            p_minus = best_sol.copy()
            p_minus[i] = max(p_minus[i] - step_sizes[i], self.LOW[i])
            candidates.append(p_minus)
        
        candidate_costs = np.array(pool.map(self.fitness, candidates))
        for i in range(len(candidates)):
            if candidate_costs[i] < best_cost:
                best_cost = candidate_costs[i]
                best_sol = candidates[i]
        
        if best_cost < self.best_cost_global:
            self.best_cost_global = best_cost
            self.best_params_global = best_sol
            if self.progress_callback: self.progress_callback(int(it*100/self.config.max_iter), f"Pulido encontr0 mejora: {best_cost:.3e}", None)


class ACORWorker(QThread):
    """Ejecuta el optimizador ACOR en un hilo separado para no bloquear la GUI."""
    progress_signal = pyqtSignal(int, str, object)
    finished_signal = pyqtSignal(object)

    def __init__(self, optimizer: ACOROptimizer, tmax_seconds, plateau_K):
        super().__init__()
        self.optimizer = optimizer
        self.tmax_seconds = tmax_seconds
        self.plateau_K = plateau_K
        self.optimizer.progress_callback = self.handle_progress

    def handle_progress(self, pct: int, msg: str, params):
        self.progress_signal.emit(pct, msg, params)

    def stop(self):
        self.optimizer.request_stop()

    def run(self):
        try:
            self.optimizer.optimize(self.tmax_seconds, self.plateau_K)
            self.finished_signal.emit(self.optimizer)
        except Exception as e:
            error_msg = f"Error en worker: {e}\n{traceback.format_exc()}"
            self.progress_signal.emit(0, error_msg, None)
            self.finished_signal.emit(self.optimizer)
