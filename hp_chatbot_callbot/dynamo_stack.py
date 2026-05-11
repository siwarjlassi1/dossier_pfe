import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dynamodb as dynamodb,
    CfnOutput,
    RemovalPolicy,
)
from constructs import Construct


class DynamoStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── Table Produits ───────────────────────────────────────────
        self.products_table = dynamodb.Table(
            self, "ProductsTable",
            table_name="hp-products",
            partition_key=dynamodb.Attribute(
                name="productId",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── Table Commandes ──────────────────────────────────────────
        self.orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="hp-orders",
            partition_key=dynamodb.Attribute(
                name="orderId",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
 
        # ── Table Réclamations ───────────────────────────────────────
        self.complaints_table = dynamodb.Table(
            self, "ComplaintsTable",
            table_name="hp-complaints",
            partition_key=dynamodb.Attribute(
                name="complaintId",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ── Outputs ──────────────────────────────────────────────────
        CfnOutput(self, "ProductsTableName",
                  value=self.products_table.table_name)
        CfnOutput(self, "OrdersTableName",
                  value=self.orders_table.table_name)
        CfnOutput(self, "ComplaintsTableName",
                  value=self.complaints_table.table_name)