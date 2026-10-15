"""A second, slightly different email sender: a duplicated capability."""


def notify(address, text):
    print(f"[orders-mail] to={address}: {text}")
    return True
