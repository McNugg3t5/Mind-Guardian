import kagglehub
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
# Import necessary libraries for quantization
try:
    import bitsandbytes
    import accelerate
    print("bitsandbytes and accelerate imported successfully.")
except ImportError:
    bitsandbytes = None
    accelerate = None
    print("bitsandbytes or accelerate not found. Quantization may not work.")


class MindGuardian:
    """
    The main class that encapsulates the application's logic,
    using a local Gemma model via transformers.
    """
    def __init__(self):
        print("Initializing Mind Guardian with local Gemma model...")
        self.tokenizer = None
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        try:
            # Download the Gemma model using kagglehub
            print(f"Attempting to download Gemma model from KaggleHub using path: google/gemma-3n/transformers/gemma-3n-e2b ...")
            GEMMA_PATH = kagglehub.model_download("google/gemma-3n/transformers/gemma-3n-e2b")
            print(f"Model downloaded to: {GEMMA_PATH}")

            # Load the tokenizer and model using transformers
            print("Loading tokenizer and model...")
            # Attempt to load the model with 8-bit quantization for potential speedup
            # Requires bitsandbytes and accelerate libraries installed.
            if bitsandbytes and accelerate and torch.cuda.is_available():
                print("Attempting to load model with 8-bit quantization...")
                self.model = AutoModelForCausalLM.from_pretrained(
                    GEMMA_PATH,
                    load_in_8bit=True, # Enable 8-bit quantization
                    torch_dtype=torch.float16 # Often used with 8-bit loading
                ).to(self.device)
                print("Model loaded with 8-bit quantization.")
            else:
                print("bitsandbytes, accelerate, or CUDA not available. Loading model without 8-bit quantization.")
                # Load without quantization if libraries or CUDA are not available
                # Keep torch_dtype=torch.bfloat16 as before, or consider torch.float32
                self.model = AutoModelForCausalLM.from_pretrained(GEMMA_PATH, torch_dtype=torch.bfloat16).to(self.device)
                print("Model loaded without quantization.")

            self.tokenizer = AutoTokenizer.from_pretrained(GEMMA_PATH)
            print("🤖 Local Gemma model loaded successfully.")

        except Exception as e:
            print(f"❌ Critical Error: Failed to download or load the local model with or without quantization. {e}")
            self.tokenizer = None
            self.model = None


    def analyze_journal(self, journal_text: str) -> str:
        if not self.model or not self.tokenizer:
            return "Sorry, the AI service is currently unavailable."
        prompt = f"Provide a gentle, non-judgemental reflection on the following journal entry, identifying potential thought patterns in a supportive way.\n\nJournal Entry: {journal_text}\n\nReflection:"
        return self._generate_response(prompt)


    def analyze_audio_transcript(self, transcript_text: str) -> str:
        if not self.model or not self.tokenizer:
            return "Sorry, the AI service is currently unavailable."
        prompt = f"Analyze the following audio transcript to infer the emotional state and respond empathetically.\n\nAudio Transcript: {transcript_text}\n\nEmotional State Analysis:"
        return self._generate_response(prompt)


    def analyze_moment(self, moment_description: str) -> str:
        if not self.model or not self.tokenizer:
            return "Sorry, the AI service is currently unavailable."
        prompt = f"Analyze the following visual moment description and ask a gentle, open-ended question to help the user explore the feeling connected to this moment.\n\nVisual Moment Description: {moment_description}\n\nQuestion:"
        return self._generate_response(prompt)

    def _generate_response(self, prompt: str) -> str:
        """Helper method to generate text using the loaded transformers model."""
        try:
            if not self.model or not self.tokenizer:
                 return "AI model not loaded."

            # Tokenize the prompt
            input_ids = self.tokenizer(prompt, return_tensors="pt").to(self.device)

            # Generate response
            generated_ids = self.model.generate(
                **input_ids,
                max_new_tokens=200,
                do_sample=True,
                temperature=0.7,
                top_k=50,
                top_p=0.95,
                num_return_sequences=1,
            )

            # Decode the generated text
            response = self.tokenizer.decode(generated_ids[0], skip_special_tokens=True)

            # Post-process the response to remove the original prompt
            if response.startswith(prompt):
                 response = response[len(prompt):].strip()

            return response.strip()

        except Exception as e:
            return f"An error occurred during text generation: {e}"