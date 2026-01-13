"""
Payment type definitions for x402 Solana
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal
from ..shared.svm.wallet import is_valid_pubkey


class PaymentRequirementsExtra(BaseModel):
    """Extra fields for Solana payment requirements"""

    fee_payer: str = Field(..., alias="feePayer")
    """Public key of the account that will pay transaction fees (typically the facilitator)"""

    @field_validator("fee_payer")
    @classmethod
    def validate_fee_payer(cls, v: str) -> str:
        """Validate that fee_payer is a valid Solana public key"""
        if not is_valid_pubkey(v):
            raise ValueError(f"Invalid Solana public key for fee_payer: {v}")
        return v

    class Config:
        populate_by_name = True


class PaymentRequirements(BaseModel):
    """Payment requirements from a resource server (received via 402 response)"""
    
    scheme: Literal["exact"] = "exact"
    """Payment scheme identifier"""
    
    network: Literal["solana", "solana-devnet", "solana-mainnet-beta"]
    """Solana network identifier"""
    
    max_amount_required: str = Field(..., alias="maxAmountRequired")
    """Maximum amount required to pay for the resource in atomic units"""
    
    asset: str
    """Address of the SPL token mint"""
    
    pay_to: str = Field(..., alias="payTo")
    """Address to pay value to (recipient's public key)"""
    
    resource: str
    """URL of the resource to pay for"""
    
    description: str
    """Description of the resource"""
    
    mime_type: str = Field("application/json", alias="mimeType")
    """MIME type of the resource response"""
    
    max_timeout_seconds: int = Field(default=60, alias="maxTimeoutSeconds")
    """Maximum time in seconds for the resource server to respond"""
    
    output_schema: Optional[Dict[str, Any]] = Field(None, alias="outputSchema")
    """Schema describing the output (optional)"""
    
    extra: PaymentRequirementsExtra
    """Solana-specific extra information (includes feePayer)"""
    
    @field_validator("max_amount_required")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        """Validate that amount is a non-negative integer string"""
        try:
            int(v)
        except ValueError:
            raise ValueError("max_amount_required must be an integer encoded as a string")
        if int(v) < 0:
            raise ValueError("max_amount_required must be non-negative")
        return v

    @field_validator("asset", "pay_to")
    @classmethod
    def validate_pubkey_fields(cls, v: str) -> str:
        """Validate that asset and pay_to are valid Solana public keys"""
        if not is_valid_pubkey(v):
            raise ValueError(f"Invalid Solana public key: {v}")
        return v

    class Config:
        populate_by_name = True


class ExactSvmPayload(BaseModel):
    """Payload for exact payment scheme on Solana"""
    
    transaction: str
    """Base64-encoded, partially-signed Solana transaction"""
    
    class Config:
        populate_by_name = True


class PaymentPayload(BaseModel):
    """Complete payment payload with scheme and network information"""
    
    x402_version: int = Field(..., alias="x402Version")
    """Protocol version (currently 1)"""
    
    scheme: Literal["exact"]
    """Payment scheme"""
    
    network: Literal["solana", "solana-devnet", "solana-mainnet-beta"]
    """Network identifier"""
    
    payload: ExactSvmPayload
    """Scheme-specific payload"""
    
    @field_validator("x402_version")
    @classmethod
    def validate_version(cls, v: int) -> int:
        if v != 1:
            raise ValueError("Only x402 version 1 is supported")
        return v
    
    class Config:
        populate_by_name = True
