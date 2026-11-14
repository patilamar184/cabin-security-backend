def test_application_imports():
    from app.main import app
    assert app.title == 'Cabin Security Management API'
    paths = {route.path for route in app.routes}
    assert '/api/auth/register' in paths
    assert '/api/device/commands' in paths
    assert '/api/door/unlock' in paths
