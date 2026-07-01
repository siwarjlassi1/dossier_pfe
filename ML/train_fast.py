import torch
from transformers import (
    MBartForConditionalGeneration,
    MBart50TokenizerFast,
    Trainer,
    TrainingArguments,
    DataCollatorForSeq2Seq
)
from datasets import load_from_disk
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION ULTRA-RAPIDE
# ============================================================================

class Config:
    MODEL_NAME = "mbart_base_model"
    
    MAX_INPUT_LENGTH = 512
    MAX_TARGET_LENGTH = 64
    
    BATCH_SIZE = 4
    EPOCHS = 1
    LEARNING_RATE = 3e-5
    WARMUP_STEPS = 50
    
    # Dataset réduit à 100 exemples
    TRAIN_SIZE = 100
    VAL_SIZE = 20
    TEST_SIZE = 20
    
    OUTPUT_DIR = "./mbart_fast"
    FINAL_MODEL_PATH = "./mbart_summarizer_final"
    
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("="*80)
print("🚀 ENTRAÎNEMENT ULTRA-RAPIDE (100 exemples, 1 époque)")
print("="*80)
print(f"\n⏰ Début : {datetime.now().strftime('%H:%M:%S')}")
print(f"🖥️ Device : {Config.DEVICE}")
print(f"⏱️ Temps estimé : 1-2 heures\n")

# Chargement dataset
print("📂 Chargement dataset...")
dataset = load_from_disk("./samsum_dataset")

# Réduction drastique
dataset['train'] = dataset['train'].select(range(Config.TRAIN_SIZE))
dataset['validation'] = dataset['validation'].select(range(Config.VAL_SIZE))
dataset['test'] = dataset['test'].select(range(Config.TEST_SIZE))

print(f"✅ Dataset : {Config.TRAIN_SIZE} exemples d'entraînement\n")

# Chargement modèle
print("📂 Chargement MBART...")
tokenizer = MBart50TokenizerFast.from_pretrained(Config.MODEL_NAME)
model = MBartForConditionalGeneration.from_pretrained(Config.MODEL_NAME)
model.to(Config.DEVICE)
print("✅ Modèle chargé\n")

tokenizer.src_lang = "en_XX"

# Détection langue
def detect_language(text):
    french_words = ['bonjour', 'merci', 'je', 'tu', 'le', 'la', 'client', 'agent']
    return "fr_XX" if sum(1 for w in french_words if w in text.lower()) > 2 else "en_XX"

# Prétraitement
def preprocess_function(examples):
    model_inputs_list = []
    labels_list = []
    
    for dialogue, summary in zip(examples['dialogue'], examples['summary']):
        tokenizer.src_lang = detect_language(dialogue)
        
        input_enc = tokenizer(dialogue, max_length=Config.MAX_INPUT_LENGTH, truncation=True, padding='max_length')
        target_enc = tokenizer(summary, max_length=Config.MAX_TARGET_LENGTH, truncation=True, padding='max_length')
        
        model_inputs_list.append(input_enc)
        labels_list.append(target_enc['input_ids'])
    
    return {
        'input_ids': [inp['input_ids'] for inp in model_inputs_list],
        'attention_mask': [inp['attention_mask'] for inp in model_inputs_list],
        'labels': labels_list
    }

print("🔄 Prétraitement...")
tokenized_dataset = dataset.map(
    preprocess_function,
    batched=True,
    remove_columns=dataset['train'].column_names,
    desc="Tokenization"
)
print("✅ Prétraitement terminé\n")

# Data collator
data_collator = DataCollatorForSeq2Seq(
    tokenizer=tokenizer,
    model=model,
    padding=True,
    label_pad_token_id=tokenizer.pad_token_id
)

# Training arguments (SANS compute_metrics pour éviter l'erreur)
training_args = TrainingArguments(
    output_dir=Config.OUTPUT_DIR,
    
    eval_strategy="no",  # Pas d'évaluation pendant l'entraînement
    save_strategy="epoch",
    save_total_limit=1,
    
    learning_rate=Config.LEARNING_RATE,
    per_device_train_batch_size=Config.BATCH_SIZE,
    per_device_eval_batch_size=Config.BATCH_SIZE,
    num_train_epochs=Config.EPOCHS,
    warmup_steps=Config.WARMUP_STEPS,
    
    logging_steps=5,
    
    fp16=False,
    report_to="none",
    push_to_hub=False,
    disable_tqdm=False
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset['train'],
    data_collator=data_collator
)

# Entraînement
print("="*80)
print("🚀 DÉBUT ENTRAÎNEMENT")
print("="*80)
print(f"\n📊 {Config.TRAIN_SIZE} exemples, {Config.EPOCHS} époque, batch {Config.BATCH_SIZE}\n")

try:
    trainer.train()
    
    print("\n✅ ENTRAÎNEMENT TERMINÉ !\n")
    
    # Sauvegarde
    print("💾 Sauvegarde...")
    model.save_pretrained(Config.FINAL_MODEL_PATH)
    tokenizer.save_pretrained(Config.FINAL_MODEL_PATH)
    print(f"✅ Sauvegardé dans {Config.FINAL_MODEL_PATH}\n")
    
    print(f"⏰ Fin : {datetime.now().strftime('%H:%M:%S')}")
    print("\n✅ SUCCÈS ! Modèle prêt !\n")
    
except Exception as e:
    print(f"\n❌ ERREUR : {e}")
    import traceback
    traceback.print_exc()
