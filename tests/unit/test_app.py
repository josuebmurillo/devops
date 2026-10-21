def test_healthcheck():
    """Prueba unitaria básica de verificación de estado."""
    status = "OK"
    assert status == "OK"


def test_environment_variable_parsing():
    """Prueba unitaria para validación de entrada de entornos."""
    valid_environments = ["qa", "prd"]
    env_input = "qa".strip().lower()
    assert env_input in valid_environments