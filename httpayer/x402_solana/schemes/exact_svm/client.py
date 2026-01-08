"""
Client-side implementation for creating Solana payments in x402
"""

from typing import Optional, List
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.message import Message
from solders.instruction import Instruction, AccountMeta
from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from ...types import PaymentPayload, PaymentRequirements, ExactSvmPayload
from ...shared.svm.rpc import create_rpc_client, get_latest_blockhash, get_block_height, get_account_info
from ...shared.svm.transaction import encode_transaction_to_base64
import base64
import struct
import json


# Token program addresses
TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
TOKEN_2022_PROGRAM = Pubkey.from_string("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb")
ASSOCIATED_TOKEN_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")


def get_associated_token_address(owner: Pubkey, mint: Pubkey) -> Pubkey:
    """
    Derive the Associated Token Address (ATA) for a given owner and mint.
    
    Args:
        owner: The owner's public key
        mint: The mint address
        
    Returns:
        The associated token address
    """
    try:
        # Try using spl-token library with conversion to solana.publickey.PublicKey
        from spl.token.instructions import get_associated_token_address as spl_get_ata
        from solana.publickey import PublicKey
        
        # Convert solders Pubkey to solana PublicKey
        owner_pk = PublicKey(str(owner))
        mint_pk = PublicKey(str(mint))
        
        # Get ATA using spl-token library
        ata_pk = spl_get_ata(owner_pk, mint_pk)
        
        # Convert back to solders Pubkey
        return Pubkey.from_string(str(ata_pk))
    except (ImportError, Exception):
        # Fallback: Manual ATA derivation
        # Seeds: [owner, token_program, mint]
        seeds = [
            bytes(owner),
            bytes(TOKEN_PROGRAM),
            bytes(mint),
        ]
        ata, _ = Pubkey.find_program_address(seeds, ASSOCIATED_TOKEN_PROGRAM)
        return ata


def create_transfer_instruction(
    source: Pubkey,
    destination: Pubkey,
    owner: Pubkey,
    amount: int,
    decimals: int = 6,
) -> Instruction:
    """
    Create an SPL token transfer instruction.
    
    Args:
        source: Source token account
        destination: Destination token account
        owner: Owner of the source account (authority)
        amount: Amount to transfer in atomic units
        decimals: Decimal places (for validation)
        
    Returns:
        Transfer instruction
    """
    try:
        # Use spl-token library for proper instruction creation
        from spl.token.instructions import transfer
        
        # Create the transfer instruction using spl-token
        # Transfer instruction format: [source, destination, authority]
        return transfer(
            {
                "program_id": TOKEN_PROGRAM,
                "source": source,
                "destination": destination,
                "authority": owner,
            },
            amount,
        )
    except (ImportError, TypeError):
        # Fallback: Manual instruction creation for Transfer (not TransferChecked)
        # Transfer instruction data: [3 (discriminator), amount (8 bytes)]
        amount_bytes = struct.pack("<Q", amount)
        data = bytes([3]) + amount_bytes
        
        # Create accounts metadata: [source, destination, authority]
        accounts = [
            AccountMeta(source, False, True),     # Source (writable)
            AccountMeta(destination, False, True), # Destination (writable)
            AccountMeta(owner, True, False),      # Authority (signer)
        ]
        
        return Instruction(
            program_id=TOKEN_PROGRAM,
            accounts=accounts,
            data=data,
        )


def create_ata_instruction(
    payer: Pubkey,
    owner: Pubkey,
    mint: Pubkey,
) -> Instruction:
    """
    Create an instruction to create an Associated Token Account.
    
    Args:
        payer: Account that will pay for the ATA creation
        owner: Owner of the new ATA
        mint: Token mint address
        
    Returns:
        Create ATA instruction
    """
    ata = get_associated_token_address(owner, mint)
    
    # ATA creation instruction has no data
    data = bytes()
    
    # Accounts: [funding, associated_token, wallet, mint, system_program, token_program]
    accounts = [
        AccountMeta(payer, True, True),                 # Funding account (signer, writable)
        AccountMeta(ata, False, True),                  # Associated token account (writable)
        AccountMeta(owner, False, False),               # Wallet address (readonly)
        AccountMeta(mint, False, False),                # Token mint (readonly)
        AccountMeta(SYSTEM_PROGRAM, False, False),      # System program (readonly)
        AccountMeta(TOKEN_PROGRAM, False, False),       # Token program (readonly)
    ]
    
    return Instruction(
        program_id=ASSOCIATED_TOKEN_PROGRAM,
        accounts=accounts,
        data=data,
    )


async def create_payment_header(
    signer: Keypair,
    x402_version: int,
    payment_requirements: PaymentRequirements,
    custom_rpc_url: Optional[str] = None,
) -> str:
    """
    Create and encode a payment header for the given client and payment requirements.
    
    Args:
        signer: Client's keypair for signing
        x402_version: Protocol version (currently 1)
        payment_requirements: Payment requirements from server
        custom_rpc_url: Optional custom RPC URL
        
    Returns:
        Base64-encoded payment header
    """
    payment_payload = await create_payment_payload(
        signer=signer,
        x402_version=x402_version,
        payment_requirements=payment_requirements,
        custom_rpc_url=custom_rpc_url,
    )
    
    # Encode the payment payload
    payload_dict = {
        "x402Version": payment_payload.x402_version,
        "scheme": payment_payload.scheme,
        "network": payment_payload.network,
        "payload": {
            "transaction": payment_payload.payload.transaction
        }
    }
    
    # Proper JSON serialization
    json_str = json.dumps(payload_dict)
    return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')


async def create_payment_payload(
    signer: Keypair,
    x402_version: int,
    payment_requirements: PaymentRequirements,
    custom_rpc_url: Optional[str] = None,
) -> PaymentPayload:
    """
    Create a payment payload containing a partially-signed Solana transaction.
    
    Args:
        signer: Client's keypair for signing
        x402_version: Protocol version (currently 1)
        payment_requirements: Payment requirements from server
        custom_rpc_url: Optional custom RPC URL
        
    Returns:
        Payment payload with signed transaction
    """
    # Create RPC URL
    rpc_url = create_rpc_client(
        network=payment_requirements.network,
        custom_url=custom_rpc_url,
    )
    
    # Create the transfer transaction
    transaction = await create_transfer_transaction(
        signer=signer,
        payment_requirements=payment_requirements,
        rpc_url=rpc_url,
    )
    
    # Sign the transaction with client's keypair (partially signed)
    # The facilitator will add their signature later as fee payer
    transaction.partial_sign([signer], transaction.message.recent_blockhash)
    
    # Encode to base64
    tx_base64 = encode_transaction_to_base64(transaction)
    
    # Return payment payload
    return PaymentPayload(
        x402_version=x402_version,
        scheme=payment_requirements.scheme,
        network=payment_requirements.network,
        payload=ExactSvmPayload(transaction=tx_base64),
    )


async def create_transfer_transaction(
    signer: Keypair,
    payment_requirements: PaymentRequirements,
    rpc_url: str,
) -> Transaction:
    """
    Create a Solana transfer transaction for the payment.
    
    This creates a transaction with:
    1. Compute budget instructions (limit and price)
    2. SPL token transfer instruction
    
    Args:
        signer: Client's keypair
        payment_requirements: Payment requirements
        rpc_url: RPC URL
        
    Returns:
        Unsigned transaction
    """
    # Parse addresses
    asset_pubkey = Pubkey.from_string(payment_requirements.asset)
    pay_to_pubkey = Pubkey.from_string(payment_requirements.pay_to)
    
    # Get client's ATA and recipient's ATA
    client_pubkey = signer.pubkey()
    client_ata = get_associated_token_address(client_pubkey, asset_pubkey)
    destination_ata = get_associated_token_address(pay_to_pubkey, asset_pubkey)
    
    # Check if ATAs exist
    client_ata_exists = await get_account_info(rpc_url, str(client_ata)) is not None
    destination_ata_exists = await get_account_info(rpc_url, str(destination_ata)) is not None
    
    # Create instructions list
    instructions: List[Instruction] = []
    
    # 1. Set compute unit price (1 microlamport = 0.000001 lamport)
    compute_price_ix = set_compute_unit_price(1_000_000)  # 1 micro lamport
    instructions.append(compute_price_ix)
    
    # 2. Set compute unit limit (increase if creating ATAs)
    compute_units = 200_000 if (not client_ata_exists or not destination_ata_exists) else 100_000
    compute_limit_ix = set_compute_unit_limit(compute_units)
    instructions.append(compute_limit_ix)
    
    # 3. Create client's ATA if it doesn't exist
    if not client_ata_exists:
        # Client pays for their own ATA
        create_client_ata_ix = create_ata_instruction(
            payer=client_pubkey,
            owner=client_pubkey,
            mint=asset_pubkey,
        )
        instructions.append(create_client_ata_ix)
    
    # 4. Create destination ATA if it doesn't exist
    # Note: Fee payer (facilitator) will pay for this
    if not destination_ata_exists:
        # Use facilitator as payer - will be set when they co-sign
        fee_payer_pubkey = Pubkey.from_string(payment_requirements.extra.fee_payer)
        create_dest_ata_ix = create_ata_instruction(
            payer=fee_payer_pubkey,
            owner=pay_to_pubkey,
            mint=asset_pubkey,
        )
        instructions.append(create_dest_ata_ix)
    
    # 5. Create SPL token transfer instruction
    amount = int(payment_requirements.max_amount_required)
    transfer_ix = create_transfer_instruction(
        source=client_ata,
        destination=destination_ata,
        owner=client_pubkey,
        amount=amount,
    )
    instructions.append(transfer_ix)
    
    # Get recent blockhash
    blockhash_bytes, last_valid_block_height = await get_latest_blockhash(rpc_url)
    recent_blockhash = Hash.from_bytes(blockhash_bytes)

    # Get current block height to validate blockhash isn't too close to expiry
    current_block_height = await get_block_height(rpc_url)

    # Validate blockhash has sufficient time before expiry
    # Solana blockhashes are valid for ~150 blocks (~60 seconds at 400ms/slot)
    blocks_until_expiry = last_valid_block_height - current_block_height
    MIN_BLOCKS_BEFORE_EXPIRY = 30  # Minimum ~12 seconds buffer

    if blocks_until_expiry < MIN_BLOCKS_BEFORE_EXPIRY:
        raise ValueError(
            f"Blockhash expires too soon (in {blocks_until_expiry} blocks, ~{blocks_until_expiry * 0.4:.1f}s). "
            f"Minimum required: {MIN_BLOCKS_BEFORE_EXPIRY} blocks (~{MIN_BLOCKS_BEFORE_EXPIRY * 0.4:.1f}s). "
            "Please try again to get a fresh blockhash."
        )

    # Create message with facilitator as fee payer (from payment requirements)
    fee_payer_pubkey = Pubkey.from_string(payment_requirements.extra.fee_payer)
    message = Message.new_with_blockhash(
        instructions,
        fee_payer_pubkey,  # Facilitator pays transaction fees
        recent_blockhash,
    )

    # Create unsigned transaction
    return Transaction.new_unsigned(message)