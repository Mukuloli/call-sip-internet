class MyState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.order_data = None
        self.customer_phone = None
        self.customer_order_number = None
        self.transfer_initiated = False
        self.should_disconnect = False

