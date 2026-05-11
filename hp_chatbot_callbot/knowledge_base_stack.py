from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_bedrock as bedrock,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct

class HpChatbotKnowledgeBaseStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # ── 1. Bucket S3 pour les documents ──
        self.documents_bucket = s3.Bucket(
            self, "HpDocumentsBucket",
            bucket_name="hp-chatbot-knowledge-base",
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True
        )

        # ── 2. Role IAM pour Bedrock KB ──
        self.kb_role = iam.Role(
            self, "KnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal(
                "bedrock.amazonaws.com"
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                )
            ]
        )

        # Permissions S3
        self.documents_bucket.grant_read(self.kb_role)

        # ── 3. Knowledge Base Bedrock ──
        self.knowledge_base = bedrock.CfnKnowledgeBase(
            self, "HpKnowledgeBase",
            name="hp-support-knowledge-base",
            description="Base de connaissance HP Support",
            role_arn=self.kb_role.role_arn,
            knowledge_base_configuration=
                bedrock.CfnKnowledgeBase\
                    .KnowledgeBaseConfigurationProperty(
                type="VECTOR",
                vector_knowledge_base_configuration=
                    bedrock.CfnKnowledgeBase\
                        .VectorKnowledgeBaseConfigurationProperty(
                    embedding_model_arn=(
                        "arn:aws:bedrock:us-east-1::foundation-model/"
                        "amazon.titan-embed-text-v1"
                    )
                )
            ),
            storage_configuration=
                bedrock.CfnKnowledgeBase\
                    .StorageConfigurationProperty(
                type="OPENSEARCH_SERVERLESS",
                opensearch_serverless_configuration=
                    bedrock.CfnKnowledgeBase\
                        .OpenSearchServerlessConfigurationProperty(
                    collection_arn=(
                        f"arn:aws:aoss:us-east-1:"
                        f"{self.account}:collection/hp-kb-collection"
                    ),
                    field_mapping=
                        bedrock.CfnKnowledgeBase\
                            .OpenSearchServerlessFieldMappingProperty(
                        metadata_field="metadata",
                        text_field="text",
                        vector_field="embedding"
                    ),
                    vector_index_name="hp-kb-index"
                )
            )
        )

        # ── 4. Data Source (S3 → KB) ──
        self.data_source = bedrock.CfnDataSource(
            self, "HpDataSource",
            name="hp-documents-source",
            knowledge_base_id=self.knowledge_base.ref,
            data_source_configuration=
                bedrock.CfnDataSource\
                    .DataSourceConfigurationProperty(
                type="S3",
                s3_configuration=
                    bedrock.CfnDataSource\
                        .S3DataSourceConfigurationProperty(
                    bucket_arn=self.documents_bucket.bucket_arn,
                    inclusion_prefixes=["documents/"]
                )
            )
        )

        # ── 5. Outputs ──
        CfnOutput(
            self, "KnowledgeBaseId",
            value=self.knowledge_base.ref,
            description="ID de la Knowledge Base"
        )

        CfnOutput(
            self, "DocumentsBucketName",
            value=self.documents_bucket.bucket_name,
            description="Bucket S3 des documents HP"
        )
