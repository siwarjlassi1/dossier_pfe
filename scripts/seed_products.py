import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('hp-products')

products = [
    {
        "productId": "m12",
        "name": "HP LaserJet M12",
        "type": "printer",
        "price": Decimal("299.99"),
        "stock": 50,
        "description": "HP LaserJet Pro M12 - Imprimante laser monochrome",
    },
    {
        "productId": "m26",
        "name": "HP LaserJet M26",
        "type": "printer",
        "price": Decimal("399.99"),
        "stock": 30,
        "description": "HP LaserJet Pro M26 - Imprimante laser multifonction",
    },
    {
        "productId": "elitebook840",
        "name": "HP EliteBook 840",
        "type": "laptop",
        "price": Decimal("1299.99"),
        "stock": 20,
        "description": "HP EliteBook 840 G9 - Ordinateur portable professionnel",
    },
    {
        "productId": "probook450",
        "name": "HP ProBook 450",
        "type": "laptop",
        "price": Decimal("899.99"),
        "stock": 35,
        "description": "HP ProBook 450 G9 - Ordinateur portable business",
    },
    {
        "productId": "elitepad1000",
        "name": "HP ElitePad 1000",
        "type": "tablet",
        "price": Decimal("799.99"),
        "stock": 15,
        "description": "HP ElitePad 1000 G2 - Tablette professionnelle",
    },
]

def seed():
    print("Insertion des produits dans hp-products...")
    for product in products:
        table.put_item(Item=product)
        print(f"  ✅ {product['productId']} - {product['name']}")
    print(f"\nTotal : {len(products)} produits insérés avec succès !")

if __name__ == "__main__":
    seed()