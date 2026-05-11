import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_lex as lex,
    aws_iam as iam,
    CfnOutput,
)
from constructs import Construct

#Rôle : Crée le bot Amazon Lex qui comprend le langage naturel


class LexStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, orchestrator_arn, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        lex_role = iam.Role(
            self, "HpChatbotLexRole",
            assumed_by=iam.ServicePrincipal("lexv2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonLexFullAccess")
            ],
        )

        def make_slot(name, slot_type, prompt):
            return lex.CfnBot.SlotProperty(
                name=name,
                slot_type_name=slot_type,
                value_elicitation_setting=lex.CfnBot.SlotValueElicitationSettingProperty(
                    slot_constraint="Required",
                    prompt_specification=lex.CfnBot.PromptSpecificationProperty(
                        message_groups_list=[
                            lex.CfnBot.MessageGroupProperty(
                                message=lex.CfnBot.MessageProperty(
                                    plain_text_message=lex.CfnBot.PlainTextMessageProperty(
                                        value=prompt
                                    )
                                )
                            )
                        ],
                        max_retries=3,
                    ),
                ),
            )

        def make_slot_optional(name, slot_type, prompt):
            return lex.CfnBot.SlotProperty(
                name=name,
                slot_type_name=slot_type,
                value_elicitation_setting=lex.CfnBot.SlotValueElicitationSettingProperty(
                    slot_constraint="Optional",
                    prompt_specification=lex.CfnBot.PromptSpecificationProperty(
                        message_groups_list=[
                            lex.CfnBot.MessageGroupProperty(
                                message=lex.CfnBot.MessageProperty(
                                    plain_text_message=lex.CfnBot.PlainTextMessageProperty(
                                        value=prompt
                                    )
                                )
                            )
                        ],
                        max_retries=3,
                    ),
                ),
            )

        def make_utterances(*texts):
            return [lex.CfnBot.SampleUtteranceProperty(utterance=t) for t in texts]

        def make_priority(priority, slot_name):
            return lex.CfnBot.SlotPriorityProperty(
                priority=priority,
                slot_name=slot_name
            )

        def make_fulfillment():
            return lex.CfnBot.FulfillmentCodeHookSettingProperty(enabled=True)

        def make_dialog_hook():
            return lex.CfnBot.DialogCodeHookSettingProperty(enabled=True)

        # ── Locale EN ─────────────────────────────────────────────────
        locale_en = lex.CfnBot.BotLocaleProperty(
            locale_id="en_US",
            nlu_confidence_threshold=0.30,
            intents=[

                lex.CfnBot.IntentProperty(
                    name="Salutation",
                    sample_utterances=make_utterances(
                        "Hello", "Hi", "Hey", "Good morning"
                    ),
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── CommanderProduit EN ──────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="CommanderProduit",
                    sample_utterances=make_utterances(
                        "I want to order a product",
                        "I would like to buy",
                        "Order a product",
                        "I want to buy a printer",
                        "I want to buy a laptop",
                        "I want to buy a tablet",
                        "Purchase a product",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "ProductType",
                            "AMAZON.AlphaNumeric",
                            "What product would you like to order? (printer, laptop, tablet...)"
                        ),
                        make_slot(
                            "ProductReference",
                            "AMAZON.AlphaNumeric",
                            "What is the reference of the product? (e.g. m12, m26, elitebook840)"
                        ),
                        make_slot_optional(
                            "PaymentMethod",
                            "AMAZON.AlphaNumeric",
                            "How would you like to pay? (Cash or Card)"
                        ),
                        make_slot_optional(
                            "CardNumber",
                            "AMAZON.AlphaNumeric",
                            "Please enter your credit card number:"
                        ),
                        make_slot_optional(
                            "CardCVV",
                            "AMAZON.AlphaNumeric",
                            "Please enter your CVV/CVC code:"
                        ),
                    ],
                    slot_priorities=[
                        make_priority(1, "ProductType"),
                        make_priority(2, "ProductReference"),
                        make_priority(3, "PaymentMethod"),
                        make_priority(4, "CardNumber"),
                        make_priority(5, "CardCVV"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── ReclamerPanne EN ─────────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="ReclamerPanne",
                    sample_utterances=make_utterances(
                        "I want to report a problem",
                        "I have a problem with my product",
                        "My printer is broken",
                        "Report a problem",
                        "I want to file a complaint",
                        "My product is not working",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "ProductType",
                            "AMAZON.AlphaNumeric",
                            "What type of product has the problem? (printer, laptop, tablet...)"
                        ),
                        make_slot(
                            "ProductReference",
                            "AMAZON.AlphaNumeric",
                            "What is the reference of the product?"
                        ),
                        make_slot_optional(
                            "UnderWarranty",
                            "AMAZON.AlphaNumeric",
                            "Is your product under warranty? (yes/no)"
                        ),
                        make_slot_optional(
                            "ProblemDescription",
                            "AMAZON.FreeFormInput",
                            "Please describe the problem:"
                        ),
                        make_slot_optional(
                            "CustomerEmail",
                            "AMAZON.FreeFormInput",
                            "What is your email address to receive the confirmation?"
                        )
                    ],
                    slot_priorities=[
                        make_priority(1, "ProductType"),
                        make_priority(2, "ProductReference"),
                        make_priority(3, "UnderWarranty"),
                        make_priority(4, "ProblemDescription"),
                        make_priority(5,"CustomerEmail"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── VerifierCommande EN ──────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="VerifierCommande",
                    sample_utterances=make_utterances(
                        "I want to check my order",
                        "Check my order",
                        "Track my order",
                        "Where is my order",
                        "Order status"
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "OrderId",
                            "AMAZON.AlphaNumeric",
                            "Please enter your order ID"
                        ),
                    ],
                    slot_priorities=[
                        make_priority(1, "OrderId"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── AnnulerCommande EN ───────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="AnnulerCommande",
                    sample_utterances=make_utterances(
                        "I want to cancel my order",
                        "Cancel my order",
                        "Cancel order",
                        "I want to cancel",
                        "Cancel my purchase",
                        "I would like to cancel my order",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot_optional(
                            "OrderId",
                            "AMAZON.AlphaNumeric",
                            "Please enter your order ID:"
                        ),
                    ],
                    slot_priorities=[
                        make_priority(1, "OrderId"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),


                # ── SuivreReclamation EN ─────────────────────────────
            lex.CfnBot.IntentProperty(
                name="SuivreReclamation",
                sample_utterances=make_utterances(
                    "I want to track my claim",
                    "Track my complaint",
                    "What is the status of my claim",
                    "Check my complaint",
                    "Follow up on my claim",
                    "Where is my complaint",
                    "Claim status",
                    "I want to check my complaint",
                ),
                dialog_code_hook=make_dialog_hook(),
                slots=[
                    make_slot(
                        "ReclamationId",
                        "AMAZON.AlphaNumeric",
                        "Please enter your claim ID:"
                        ),
                        ],
                slot_priorities=[
                    make_priority(1, "ReclamationId"),
                    ],
                fulfillment_code_hook=make_fulfillment(),
                ),



                # ── DemanderDepannage EN ─────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="DemanderDepannage",
                    sample_utterances=make_utterances(
                        "I have a problem with my printer",
                        "My printer has a paper jam",
                        "My laptop won't start",
                        "My screen is black",
                        "My battery is not charging",
                        "My printer is not printing",
                        "How do I fix my printer",
                        "My EliteBook is not working",
                        "I need help with my printer",
                        "I need technical support",
                        "My device is not working",
                        "Help me fix my product",
                        "Technical issue with my printer",
                        "My M12 has a paper jam",
                        "My M26 is not printing",
                        ),
                        fulfillment_code_hook=make_fulfillment(),
                        ),

                

                lex.CfnBot.IntentProperty(
                    name="FallbackIntent",
                    parent_intent_signature="AMAZON.FallbackIntent",
                    fulfillment_code_hook=make_fulfillment(),
                ),
            ],
        )

        # ── Locale FR ─────────────────────────────────────────────────
        locale_fr = lex.CfnBot.BotLocaleProperty(
            locale_id="fr_FR",
            nlu_confidence_threshold=0.30,
            intents=[

                lex.CfnBot.IntentProperty(
                    name="Salutation",
                    sample_utterances=make_utterances(
                        "Bonjour", "Salut", "Bonsoir"
                    ),
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── CommanderProduit FR ──────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="CommanderProduit",
                    sample_utterances=make_utterances(
                        "Je veux commander un produit",
                        "Je voudrais acheter",
                        "Commander un produit",
                        "Je veux acheter une imprimante",
                        "Je veux acheter un ordinateur",
                        "Passer une commande",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "ProductType",
                            "AMAZON.AlphaNumeric",
                            "Quel produit souhaitez-vous commander ? (imprimante, ordinateur, tablette...)"
                        ),
                        make_slot(
                            "ProductReference",
                            "AMAZON.AlphaNumeric",
                            "Quelle est la référence du produit ? (ex: m12, m26, elitebook840)"
                        ),
                        make_slot_optional(
                            "PaymentMethod",
                            "AMAZON.AlphaNumeric",
                            "Comment souhaitez-vous payer ? (Cash ou Carte)"
                        ),
                        make_slot_optional(
                            "CardNumber",
                            "AMAZON.AlphaNumeric",
                            "Veuillez entrer votre numéro de carte bancaire :"
                        ),
                        make_slot_optional(
                            "CardCVV",
                            "AMAZON.AlphaNumeric",
                            "Veuillez entrer votre code CVV/CVC :"
                        ),
                    ],
                    slot_priorities=[
                        make_priority(1, "ProductType"),
                        make_priority(2, "ProductReference"),
                        make_priority(3, "PaymentMethod"),
                        make_priority(4, "CardNumber"),
                        make_priority(5, "CardCVV"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── ReclamerPanne FR ─────────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="ReclamerPanne",
                    sample_utterances=make_utterances(
                        "Je veux signaler un problème",
                        "J'ai un problème avec mon produit",
                        "Mon imprimante est en panne",
                        "Signaler une panne",
                        "Je veux faire une réclamation",
                        "Mon produit ne fonctionne pas",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "ProductType",
                            "AMAZON.AlphaNumeric",
                            "Quel type de produit a le problème ? (imprimante, ordinateur, tablette...)"
                        ),
                        make_slot(
                            "ProductReference",
                            "AMAZON.AlphaNumeric",
                            "Quelle est la référence du produit ?"
                        ),
                        make_slot_optional(
                            "UnderWarranty",
                            "AMAZON.AlphaNumeric",
                            "Votre produit est-il sous garantie ? (oui/non)"
                        ),
                        make_slot_optional(
                            "ProblemDescription",
                            "AMAZON.FreeFormInput",
                            "Veuillez décrire le problème :"
                        ),
                        make_slot_optional(
                            "CustomerEmail",
                            "AMAZON.FreeFormInput",
                            "Quel est votre adresse email pour recevoir la confirmation ?"
                        )
                    ],
                    slot_priorities=[
                        make_priority(1, "ProductType"),
                        make_priority(2, "ProductReference"),
                        make_priority(3, "UnderWarranty"),
                        make_priority(4, "ProblemDescription"),
                        make_priority(5,"CustomerEmail"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── VerifierCommande FR ──────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="VerifierCommande",
                    sample_utterances=make_utterances(
                        "Je veux vérifier ma commande",
                        "Vérifier ma commande",
                        "Quel est le statut de ma commande",
                        "Où est ma commande",
                        "Suivre ma commande"
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "OrderId",
                            "AMAZON.AlphaNumeric",
                            "Veuillez entrer votre numéro de commande"
                        ),
                    ],
                    slot_priorities=[
                        make_priority(1, "OrderId"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),

                # ── AnnulerCommande FR ───────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="AnnulerCommande",
                    sample_utterances=make_utterances(
                        "Je veux annuler ma commande",
                        "Annuler ma commande",
                        "Annuler commande",
                        "Je veux annuler",
                        "Annuler mon achat",
                        "Je souhaite annuler ma commande",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot_optional(
                            "OrderId",
                            "AMAZON.AlphaNumeric",
                            "Veuillez entrer votre numéro de commande :"
                        ),
                    ],
                    slot_priorities=[
                        make_priority(1, "OrderId"),
                    ],
                    fulfillment_code_hook=make_fulfillment(),
                ),


                # ── SuivreReclamation FR ─────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="SuivreReclamation",
                    sample_utterances=make_utterances(
                        "Je veux suivre ma réclamation",
                        "Suivre ma réclamation",
                        "Quel est le statut de ma réclamation",
                        "Vérifier ma réclamation",
                        "Où en est ma réclamation",
                        "Statut de ma réclamation",
                        "Je veux vérifier ma réclamation",
                        "Suivi réclamation",
                    ),
                    dialog_code_hook=make_dialog_hook(),
                    slots=[
                        make_slot(
                            "ReclamationId",
                            "AMAZON.AlphaNumeric",
                            "Veuillez entrer votre numéro de réclamation :"
                            ),
                            ],
                    slot_priorities=[
                        make_priority(1, "ReclamationId"),
                        ],
                    fulfillment_code_hook=make_fulfillment(),
                ),




                # ── DemanderDepannage FR ─────────────────────────────
                lex.CfnBot.IntentProperty(
                    name="DemanderDepannage",
                    sample_utterances=make_utterances(
                        "J'ai un problème avec mon imprimante",
                        "Mon imprimante fait un bourrage papier",
                        "Mon ordinateur ne démarre pas",
                        "Mon écran est noir",
                        "Ma batterie ne charge plus",
                        "Mon imprimante n'imprime plus",
                        "Comment réparer mon imprimante",
                        "Mon EliteBook ne fonctionne pas",
                        "J'ai besoin d'aide avec mon imprimante",
                        "J'ai besoin d'assistance technique",
                        "Mon appareil ne fonctionne pas",
                        "Aidez moi à réparer mon produit",
                        "Problème technique avec mon imprimante",
                        "Mon M12 fait un bourrage papier",
                        "Mon M26 n'imprime plus",
                        "Dépannage imprimante",
                        "Dépanner mon ordinateur",
                        "J'ai un bourrage papier sur mon imprimante M12",
                        ),
                        fulfillment_code_hook=make_fulfillment(),
                        ),


                lex.CfnBot.IntentProperty(
                    name="FallbackIntent",
                    parent_intent_signature="AMAZON.FallbackIntent",
                    fulfillment_code_hook=make_fulfillment(),
                ),
            ],
        )

        bot = lex.CfnBot(
            self,
            "HpChatbot",
            name="HpChatbot",
            role_arn=lex_role.role_arn,
            data_privacy={"ChildDirected": False},
            idle_session_ttl_in_seconds=300,
            bot_locales=[locale_en, locale_fr],
        )

        bot_version = lex.CfnBotVersion(
            self,
            "HpChatbotVersion8",
            bot_id=bot.ref,
            bot_version_locale_specification=[
                lex.CfnBotVersion.BotVersionLocaleSpecificationProperty(
                    locale_id="en_US",
                    bot_version_locale_details=lex.CfnBotVersion.BotVersionLocaleDetailsProperty(
                        source_bot_version="DRAFT"
                    )
                ),
                lex.CfnBotVersion.BotVersionLocaleSpecificationProperty(
                    locale_id="fr_FR",
                    bot_version_locale_details=lex.CfnBotVersion.BotVersionLocaleDetailsProperty(
                        source_bot_version="DRAFT"
                    )
                ),
            ],
        )

        bot_alias = lex.CfnBotAlias(
            self,
            "HpChatbotAlias",
            bot_id=bot.ref,
            bot_alias_name="HpChatbotProd",
            bot_version=bot_version.attr_bot_version,
            bot_alias_locale_settings=[
                lex.CfnBotAlias.BotAliasLocaleSettingsItemProperty(
                    locale_id="en_US",
                    bot_alias_locale_setting=lex.CfnBotAlias.BotAliasLocaleSettingsProperty(
                        enabled=True,
                        code_hook_specification=lex.CfnBotAlias.CodeHookSpecificationProperty(
                            lambda_code_hook=lex.CfnBotAlias.LambdaCodeHookProperty(
                                lambda_arn=orchestrator_arn,
                                code_hook_interface_version="1.0"
                            )
                        )
                    )
                ),
                lex.CfnBotAlias.BotAliasLocaleSettingsItemProperty(
                    locale_id="fr_FR",
                    bot_alias_locale_setting=lex.CfnBotAlias.BotAliasLocaleSettingsProperty(
                        enabled=True,
                        code_hook_specification=lex.CfnBotAlias.CodeHookSpecificationProperty(
                            lambda_code_hook=lex.CfnBotAlias.LambdaCodeHookProperty(
                                lambda_arn=orchestrator_arn,
                                code_hook_interface_version="1.0"
                            )
                        )
                    )
                ),
            ]
        )

        self.bot_id = bot.ref
        self.bot_alias_id = bot_alias.attr_bot_alias_id

        CfnOutput(self, "BotId", value=bot.ref)
        CfnOutput(self, "BotAliasId", value=bot_alias.attr_bot_alias_id)
