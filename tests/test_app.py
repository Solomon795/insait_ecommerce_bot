# tests/test_app.py
import pytest
from flask import session

def test_index(client):
    """Test the index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to E-Commerce Support Bot!" in response.data

def test_order_status_request(client):
    """Test order status request handling."""
    response = client.get('/get', query_string={'msg': 'What is my order status?'})
    assert response.status_code == 200
    assert b"Could you please provide your order ID in the following format" in response.data

def test_switch_to_human_request(client):
    """Test switch to human request handling."""
    response = client.get('/get', query_string={'msg': 'I want to talk to a human'})
    assert response.status_code == 200
    assert b"I understand your request for real person interaction" in response.data

def test_invalid_order_id(client):
    """Test handling of invalid order ID."""
    with client.session_transaction() as sess:
        sess['order_status'] = True

    response = client.get('/get', query_string={'msg': '1234-1234567'})
    assert response.status_code == 200
    assert b"The order ID should be in the format XXX-XXXXXXX" in response.data

def test_cancel_process(client):
    """Test cancelling the process."""
    with client.session_transaction() as sess:
        sess['order_status'] = True

    response = client.get('/get', query_string={'msg': 'cancel'})
    assert response.status_code == 200
    assert b"Certainly. How else can I help you?" in response.data
    with client.session_transaction() as sess:
        assert 'order_status' not in sess