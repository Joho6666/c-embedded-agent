from app.config.settings import settings


def test_max_iterations_bounded():
    assert 1 <= settings.max_agent_iterations <= 32
