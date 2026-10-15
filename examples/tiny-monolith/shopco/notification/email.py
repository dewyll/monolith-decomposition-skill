SENT = []


def send_email(address, text):
    SENT.append((address, text))
    print(f"[mail] to={address}: {text}")
