from pydantic import BaseModel, HttpUrl


class CheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: HttpUrl
    cancel_url: HttpUrl


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
