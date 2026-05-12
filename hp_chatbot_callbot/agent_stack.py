import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_lambda as lambda_,
    CfnOutput,
)
from constructs import Construct
from hp_chatbot_callbot.dynamo_stack import DynamoStack


class AgentStack(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 dynamo_stack: DynamoStack,
                 api_url: str,
                 knowledge_base_id: str,
                 **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. Rôle IAM pour les Lambdas Action Groups ────────────────
        # Pourquoi ? Les Lambdas ont besoin d'accéder à DynamoDB
        # et aux logs CloudWatch
        self.lambda_role = iam.Role(
            self, "HpAgentLambdaRole",
            role_name="hp-agent-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ]
        )

        # Accès DynamoDB pour les Lambdas
        dynamo_stack.products_table.grant_read_data(self.lambda_role)
        dynamo_stack.orders_table.grant_read_write_data(self.lambda_role)
        dynamo_stack.complaints_table.grant_read_write_data(self.lambda_role)

        # ── 2. Rôle IAM pour l'Agent Bedrock ─────────────────────────
        self.agent_role = iam.Role(
            self, "HpAgentRole",
            role_name="hp-chatbot-agent-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )

        # Permission : invoquer Claude 3 Haiku
        self.agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeAgent",          # ← Ajout important
                ],
                resources=[
                    "arn:aws:bedrock:us-east-1::foundation-model/"
                    "anthropic.claude-3-5-haiku-20241022-v1:0"
                ]
            )
        )

        # Permission : accéder à la Knowledge Base
        self.agent_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate",
                ],
                resources=[
                    f"arn:aws:bedrock:us-east-1:"
                    f"{self.account}:knowledge-base/{knowledge_base_id}"
                ]
            )
        )

        # Permission : accéder à DynamoDB (pour l'agent directement)
        dynamo_stack.products_table.grant_read_data(self.agent_role)
        dynamo_stack.orders_table.grant_read_write_data(self.agent_role)
        dynamo_stack.complaints_table.grant_read_write_data(self.agent_role)

        # ── 3. Lambdas des Action Groups ──────────────────────────────
        common_env = {
            "API_GATEWAY_URL": api_url,
            # Variables DynamoDB directement accessibles
            "PRODUCTS_TABLE": dynamo_stack.products_table.table_name,
            "ORDERS_TABLE": dynamo_stack.orders_table.table_name,
            "COMPLAINTS_TABLE": dynamo_stack.complaints_table.table_name,
        }

        self.lambda_commander = lambda_.Function(
            self, "LambdaCommanderProduit",
            function_name="hp-agent-commander-produit",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                "lambda/agent_actions/commander_produit"
            ),
            role=self.lambda_role,          # ← Rôle IAM explicite
            environment=common_env,
            timeout=cdk.Duration.seconds(30),
        )

        self.lambda_reclamer = lambda_.Function(
            self, "LambdaReclamerPanne",
            function_name="hp-agent-reclamer-panne",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                "lambda/agent_actions/reclamer_panne"
            ),
            role=self.lambda_role,          # ← Rôle IAM explicite
            environment=common_env,
            timeout=cdk.Duration.seconds(30),
        )

        self.lambda_verifier = lambda_.Function(
            self, "LambdaVerifierCommande",
            function_name="hp-agent-verifier-commande",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                "lambda/agent_actions/verifier_commande"
            ),
            role=self.lambda_role,          # ← Rôle IAM explicite
            environment=common_env,
            timeout=cdk.Duration.seconds(30),
        )

        self.lambda_annuler = lambda_.Function(
            self, "LambdaAnnulerCommande",
            function_name="hp-agent-annuler-commande",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset(
                "lambda/agent_actions/annuler_commande"
            ),
            role=self.lambda_role,          # ← Rôle IAM explicite
            environment=common_env,
            timeout=cdk.Duration.seconds(30),
        )

        # ── 4. Permissions : Agent peut invoquer les Lambdas ──────────
        for fn in [
            self.lambda_commander,
            self.lambda_reclamer,
            self.lambda_verifier,
            self.lambda_annuler,
        ]:
            fn.add_permission(
                "AllowBedrock",
                principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
                action="lambda:InvokeFunction",
            )

        # ── 5. Instructions de l'Agent (Prompt Système) ───────────────
        agent_instruction = """
        Tu es un assistant virtuel HP (Hewlett-Packard) intelligent
        et professionnel. Tu aides les clients HP avec :

        1. COMMANDER UN PRODUIT :
           → Quand un client veut acheter un produit HP
           → Tu collectes : le modèle du produit et la quantité
           → Tu utilises l'action CommanderProduit

        2. RÉCLAMER UNE PANNE :
           → Quand un client a un problème technique avec son produit
           → Tu collectes : le modèle du produit et la description du problème
           → Tu utilises l'action ReclamerPanne

        3. VÉRIFIER UNE COMMANDE :
           → Quand un client veut connaître le statut de sa commande
           → Tu collectes : l'ID de la commande
           → Tu utilises l'action VerifierCommande

        4. ANNULER UNE COMMANDE :
           → Quand un client veut annuler sa commande
           → Tu collectes : l'ID de la commande
           → Tu utilises l'action AnnulerCommande

        5. DÉPANNAGE TECHNIQUE :
           → Quand un client a besoin d'aide technique
           → Tu consultes AUTOMATIQUEMENT la base de connaissance HP
           → Tu effectues PLUSIEURS recherches si nécessaire
           → Tu fournis des instructions claires et précises
           → Tu n'inventes jamais d'informations techniques

        RÈGLES IMPORTANTES :
        → Toujours être poli et professionnel
        → Toujours confirmer les informations avant d'agir
        → Si tu manques d'informations, demande-les poliment
        → Réponds toujours en français
        → Ne jamais inventer des informations sur les produits HP
        → Si la KB ne contient pas l'information, dis-le clairement
        """

        # ── 6. Création de l'Agent Bedrock ────────────────────────────
        self.agent = bedrock.CfnAgent(
            self, "HpChatbotAgent",
            agent_name="hp-chatbot-agent",
            description="Agent IA HP pour chatbot et callbot",
            foundation_model=(
                "anthropic.claude-3-5-haiku-20241022-v1:0"
            ),
            instruction=agent_instruction,
            idle_session_ttl_in_seconds=1800,
            agent_resource_role_arn=self.agent_role.role_arn,
            auto_prepare=True,

            # ── Mémoire conversationnelle ─────────────────────────
            # Pourquoi ? L'agent se souvient du contexte
            # de toute la conversation client
            memory_configuration=bedrock.CfnAgent.MemoryConfigurationProperty(
                enabled_memory_types=["SESSION_SUMMARY"],
                storage_days=30
            ),

            # ── Knowledge Base connectée ──────────────────────────
            knowledge_bases=[
                bedrock.CfnAgent.AgentKnowledgeBaseProperty(
                    knowledge_base_id=knowledge_base_id,
                    description=(
                        "Base de connaissance HP contenant les manuels "
                        "techniques, guides de dépannage et "
                        "documentation produits HP. Utilise cette base "
                        "pour répondre aux questions de dépannage "
                        "et support technique."
                    ),
                    knowledge_base_state="ENABLED",
                )
            ],

            # ── Action Groups ─────────────────────────────────────
            action_groups=[

                # Action 1 : Commander un produit
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="CommanderProduit",
                    description="Commander un produit HP",
                    action_group_executor=
                    bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_commander.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="commander_produit",
                                description=(
                                    "Crée une commande pour un produit HP. "
                                    "Appelle cette fonction quand le client "
                                    "veut acheter ou commander un produit HP."
                                ),
                                parameters={
                                    "modele": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Le modèle du produit HP à commander",
                                        required=True,
                                    ),
                                    "quantite": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="La quantité à commander",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),

                # Action 2 : Réclamer une panne
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="ReclamerPanne",
                    description="Enregistrer une réclamation de panne",
                    action_group_executor=
                    bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_reclamer.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="reclamer_panne",
                                description=(
                                    "Enregistre une réclamation de panne "
                                    "pour un produit HP."
                                ),
                                parameters={
                                    "modele": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Le modèle du produit HP en panne",
                                        required=True,
                                    ),
                                    "probleme": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="La description du problème technique",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),

                # Action 3 : Vérifier une commande
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="VerifierCommande",
                    description="Vérifier le statut d'une commande",
                    action_group_executor=
                    bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_verifier.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="verifier_commande",
                                description=(
                                    "Vérifie le statut d'une commande HP."
                                ),
                                parameters={
                                    "order_id": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Le numéro de commande à vérifier",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),

                # Action 4 : Annuler une commande
                bedrock.CfnAgent.AgentActionGroupProperty(
                    action_group_name="AnnulerCommande",
                    description="Annuler une commande existante",
                    action_group_executor=
                    bedrock.CfnAgent.ActionGroupExecutorProperty(
                        lambda_=self.lambda_annuler.function_arn
                    ),
                    function_schema=bedrock.CfnAgent.FunctionSchemaProperty(
                        functions=[
                            bedrock.CfnAgent.FunctionProperty(
                                name="annuler_commande",
                                description=(
                                    "Annule une commande HP existante."
                                ),
                                parameters={
                                    "order_id": bedrock.CfnAgent.ParameterDetailProperty(
                                        type="string",
                                        description="Le numéro de commande à annuler",
                                        required=True,
                                    ),
                                },
                            )
                        ]
                    ),
                ),
            ],
        )

        # ── 7. Alias de l'Agent ───────────────────────────────────────
        self.agent_alias = bedrock.CfnAgentAlias(
            self, "HpChatbotAgentAlias",
            agent_id=self.agent.ref,
            agent_alias_name="hp-agent-live",
        )

        # ── 8. Outputs ────────────────────────────────────────────────
        CfnOutput(
            self, "AgentId",
            value=self.agent.ref,
            description="ID de l'Agent Bedrock"
        )

        CfnOutput(
            self, "AgentAliasId",
            value=self.agent_alias.attr_agent_alias_id,
            description="Alias ID de l'Agent Bedrock"
        )

        # Exposer pour les autres stacks
        self.agent_id = self.agent.ref
        self.agent_alias_id = self.agent_alias.attr_agent_alias_id
