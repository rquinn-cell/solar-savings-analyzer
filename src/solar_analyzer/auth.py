import streamlit as st
import streamlit_authenticator as stauth

def get_authenticator():
    # In Option A, we define the user here. 
    # Password 'admin123' hash is provided below.
    config = {
        'credentials': {
            'usernames': {
                'rquinn': { # Your username
                    'name': 'Richard Quinn',
                    'password': '$2b$12$ehNtkKbEMBi/pwjHiuISjeXag2P4/kMO.6e2wMikwBhLUwwcS191y', # We will generate this in a second
                    'email': 'rquinn@solinservice.com'
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'solar_secure_key', # Random string
            'name': 'solar_auth_cookie'
        }
    }

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    return authenticator

def generate_hash(password):
    return stauth.Hasher([password]).generate()[0]