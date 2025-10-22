# -*- coding: utf-8 -*-
import numpy as np
from scipy.integrate import odeint

class SEIRModel:
    """Encapsula la lógica del modelo epidemiológico SEIR con una estructura de parámetros armónicos dinámica."""
    def __init__(self, harmonic_config=None):
        self.t_data = np.arange(15, dtype=float)
        self.I_data = np.array([], dtype=float)
        self.N = 763
        self.y0 = None
        self.loss_type = "MSE"
        self.huber_delta = 1.0

        self.configure_model(harmonic_config)

    def configure_model(self, harmonic_config=None):
        """(Re)genera la estructura del modelo (parámetros y límites) basado en una configuración de armónicos."""
        if harmonic_config is None:
            harmonic_config = {'beta': 2, 'gamma': 2, 'sigma': 2}
        self.harmonic_config = harmonic_config
        
        self.labels = []
        bounds_list = []
        w_idx = 1

        # Parámetros para beta
        self.labels.append("beta0")
        bounds_list.append((-1.5, 1.5))
        for i in range(1, self.harmonic_config.get('beta', 0) + 1):
            self.labels.extend([f"b{i}", f"w{w_idx}", f"p{w_idx}"])
            bounds_list.extend([(-1.5, 1.5), (-1.5, 1.5), (-2 * np.pi, 2 * np.pi)])
            w_idx += 1

        # Parámetros para gamma
        self.labels.append("gamma0")
        bounds_list.append((-1.0, 1.0))
        for i in range(1, self.harmonic_config.get('gamma', 0) + 1):
            self.labels.extend([f"g{i}", f"w{w_idx}", f"p{w_idx}"])
            bounds_list.extend([(-1.5, 1.5), (-1.5, 1.5), (-2 * np.pi, 2 * np.pi)])
            w_idx += 1

        # Parámetros para sigma
        self.labels.append("sigma0")
        bounds_list.append((-1.0, 1.0))
        for i in range(1, self.harmonic_config.get('sigma', 0) + 1):
            self.labels.extend([f"s{i}", f"w{w_idx}", f"p{w_idx}"])
            bounds_list.extend([(-1.5, 1.5), (-1.5, 1.5), (-2 * np.pi, 2 * np.pi)])
            w_idx += 1
            
        self.labels.append("k")
        bounds_list.append((0.5, 1.5))
        
        self.bounds = np.array(bounds_list, dtype=float)

    @property
    def DIM(self):
        return len(self.bounds)

    @property
    def LOW(self):
        return self.bounds[:, 0]

    @property
    def HIGH(self):
        return self.bounds[:, 1]

    def set_initial_conditions(self, k):
        """Establece las condiciones iniciales (S0, E0, I0, R0) basadas en los datos."""
        if len(self.I_data) == 0: return
        I0 = float(self.I_data[0])
        E0 = round(I0 * k)
        R0 = 0.0
        S0 = max(0.0, float(self.N) - E0 - I0 - R0)
        self.y0 = (S0, E0, I0, R0)

    def seir_harmonic(self, y, t, *p):
        """Define el sistema de EDO para el modelo SEIR con una estructura armónica dinámica."""
        S, E, I, R = y
        p_idx = 0

        # Beta dinámico
        beta_terms = self.harmonic_config.get('beta', 0)
        log_beta = p[p_idx]
        p_idx += 1
        for _ in range(beta_terms):
            log_beta += p[p_idx] * np.cos(p[p_idx+1] * t + p[p_idx+2])
            p_idx += 3
        b2_val = np.exp(log_beta)

        # Gamma dinámico
        gamma_terms = self.harmonic_config.get('gamma', 0)
        log_gamma = p[p_idx]
        p_idx += 1
        for _ in range(gamma_terms):
            log_gamma += p[p_idx] * np.cos(p[p_idx+1] * t + p[p_idx+2])
            p_idx += 3
        b3_val = np.exp(log_gamma)

        # Sigma dinámico
        sigma_terms = self.harmonic_config.get('sigma', 0)
        log_sigma = p[p_idx]
        p_idx += 1
        for _ in range(sigma_terms):
            log_sigma += p[p_idx] * np.cos(p[p_idx+1] * t + p[p_idx+2])
            p_idx += 3
        c3_val = np.exp(log_sigma)

        dS = -b2_val * S * I / self.N
        dE = b2_val * S * I / self.N - c3_val * E
        dI = c3_val * E - b3_val * I
        dR = b3_val * I
        return dS, dE, dI, dR

    def _loss(self, y_true, y_pred):
        """Calcula la p\u00e9rdida entre los datos reales y la predicci\u00f3n del modelo."""
        r = y_true - y_pred
        if self.loss_type == "MAE":
            return float(np.mean(np.abs(r)))
        elif self.loss_type == "Huber":
            d = float(self.huber_delta)
            a = np.abs(r)
            return float(np.mean(np.where(a <= d, 0.5 * (r**2), d * (a - 0.5 * d))))
        else: # MSE por defecto
            return float(np.mean(r**2))

    def fitness(self, params):
        """Función de aptitud (fitness) para la optimización. Un valor más bajo es mejor."""
        try:
            k = params[-1]  # k es siempre el último parámetro
            self.set_initial_conditions(k)
            params_ode = params[:-1]  # El resto de los parámetros son para la EDO
            
            sol = odeint(self.seir_harmonic, self.y0, self.t_data, args=tuple(params_ode), mxstep=200_000)
            I_pred = sol[:, 2]
            
            if not np.all(np.isfinite(I_pred)):
                return float("inf")
                
            return self._loss(self.I_data, I_pred)
        except Exception:
            return float("inf")

    def calculate_aic_bic(self, final_mse, num_params, num_data_points):
        """Calcula los criterios de información de Akaike (AIC) y Bayesiano (BIC)."""
        if final_mse < 1e-12 or num_data_points == 0:
            return float('inf'), float('inf')
        
        # Para el cálculo de la log-verosimilitud (log-likelihood) a partir del MSE,
        # asumimos que los errores se distribuyen normalmente.
        # RSS (Residual Sum of Squares) = MSE * n
        # Log-Likelihood: L = -n/2 * (log(2*pi) + log(RSS/n) + 1)
        # Esto se simplifica a: L = -n/2 * (log(2*pi) + log(MSE) + 1)
        log_likelihood = -num_data_points / 2.0 * (np.log(2 * np.pi) + np.log(final_mse) + 1)
        
        aic = 2 * num_params - 2 * log_likelihood
        bic = num_params * np.log(num_data_points) - 2 * log_likelihood
        
        return aic, bic

