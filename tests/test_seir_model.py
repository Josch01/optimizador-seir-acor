
import numpy as np
from clases.seir_model import SEIRModel

def test_seir_model_initialization():
    """
    Test that the SEIRModel can be initialized and its default values are correct.
    """
    model = SEIRModel()
    assert model.N == 763
    assert model.DIM == 22
    assert model.bounds.shape == (22, 2)
    assert len(model.labels) == 22

def test_seir_model_set_initial_conditions():
    """
    Test the logic for setting initial conditions.
    """
    model = SEIRModel()
    model.N = 1000
    model.I_data = np.array([10, 20, 30])
    k = 1.5 # E0 should be I0 * k = 10 * 1.5 = 15
    
    model.set_initial_conditions(k)
    
    S0, E0, I0, R0 = model.y0
    
    assert I0 == 10
    assert E0 == 15
    assert R0 == 0
    assert S0 == 1000 - 10 - 15 - 0

def test_seir_harmonic_equation_runs():
    """
    Test that the differential equation function runs without errors and returns correct shape.
    """
    model = SEIRModel()
    model.N = 1000
    model.I_data = np.array([10])
    model.set_initial_conditions(k=1.5)
    
    # Use default parameters from the model's bounds (e.g., the mean of the bounds)
    params = model.bounds.mean(axis=1)
    
    y0 = model.y0
    t = 0
    
    derivatives = model.seir_harmonic(y0, t, *params[:21])
    
    assert isinstance(derivatives, tuple)
    assert len(derivatives) == 4
    assert all(isinstance(d, float) for d in derivatives)

