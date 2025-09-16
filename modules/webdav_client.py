from webdav3.client import Client

def get_client(host, username, password):
    if not host.startswith("http"):
        host = "https://" + host
    options = {
        "webdav_hostname": host,
        "webdav_login": username,
        "webdav_password": password,
    }
    return Client(options)

def test_connection(client):
    try:
        client.list("/")
        return True
    except Exception as e:
        return False, str(e)
