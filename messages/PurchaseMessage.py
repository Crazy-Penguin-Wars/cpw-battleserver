async def handle_PurchaseMessage(reader, writer, message):
    return {
        "t": 14,
        writer.userId: {
            "earnedItems": [
                {
                    "item_id": "Pistol",
                    "amount": 1
                }
            ]
        }
    }