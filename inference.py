import torch
import torch.nn as nn
from torchvision import models
import os
import numpy as np
import cv2
from PIL import Image
from preprocessing import Preprocessor

class AlzheimerPredictor:
    def __init__(self, model_path):
        self.device = torch.device("cpu") # Keep CPU for Mac stability
        print(f"🧠 Loading Model on: {self.device}")
        
        self.class_names = ['Mild Demented', 'Moderate Demented', 'Non Demented', 'Very Mild Demented']
        self.model = self._build_model()
        
        if os.path.exists(model_path):
            state_dict = torch.load(model_path, map_location=self.device)
            # Fix DataParallel keys
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    new_state_dict[k[7:]] = v
                else:
                    new_state_dict[k] = v
            self.model.load_state_dict(new_state_dict)
            self.model.eval()
            self.model.to(self.device)
            print("✅ Model Weights Loaded.")
        else:
            raise FileNotFoundError(f"Model not found at {model_path}")

        self.preprocessor = Preprocessor()

        # Variables for Grad-CAM hooks
        self.gradients = None
        self.activations = None

    def _build_model(self):
        model = models.resnet50(weights=None)
        num_ftrs = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Linear(num_ftrs, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 4)
        )
        return model

    # --- HOOKS FOR GRAD-CAM ---
    def hook_backward(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]

    def hook_forward(self, module, input, output):
        self.activations = output

    def predict_with_heatmap(self, image_path):
        """
        Returns: Prediction, Confidence, and the Heatmap Overlay Image
        """
        # 1. Preprocess
        tensor = self.preprocessor.load_and_preprocess(image_path)
        if tensor is None: return "Error", 0.0, None
        tensor = tensor.to(self.device)

        # 2. Register Hooks on the last convolutional layer (layer4)
        target_layer = self.model.layer4[-1]
        handle_b = target_layer.register_full_backward_hook(self.hook_backward)
        handle_f = target_layer.register_forward_hook(self.hook_forward)

        # 3. Forward Pass
        self.model.zero_grad()
        output = self.model(tensor)
        probabilities = torch.nn.functional.softmax(output, dim=1)
        confidence, predicted_idx = torch.max(probabilities, 1)

        # 4. Backward Pass (to get gradients)
        output[0, predicted_idx].backward()

        # 5. Generate Heatmap
        grads = self.gradients.cpu().data.numpy()[0]
        fmap = self.activations.cpu().data.numpy()[0]
        weights = np.mean(grads, axis=(1, 2))

        cam = np.zeros(fmap.shape[1:], dtype=np.float32)
        for i, w in enumerate(weights):
            cam += w * fmap[i]
        
        cam = np.maximum(cam, 0)
        cam = cv2.resize(cam, (224, 224))
        cam = (cam - np.min(cam)) / (np.max(cam) + 1e-8)

        # 6. Create Overlay Image
        heatmap_colored = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
        
        # Get original image resized to 224x224 for blending
        # We cheat a bit and grab the tensor data to show exactly what the model saw
        orig_img = tensor.squeeze().permute(1, 2, 0).cpu().numpy()
        # Denormalize
        orig_img = orig_img * np.array([0.229, 0.224, 0.225]) + np.array([0.485, 0.456, 0.406])
        orig_img = np.clip(orig_img, 0, 1)
        orig_img = (orig_img * 255).astype(np.uint8)

        overlay = cv2.addWeighted(orig_img, 0.6, heatmap_colored, 0.4, 0)
        overlay_pil = Image.fromarray(overlay)

        # Cleanup
        handle_b.remove()
        handle_f.remove()

        return self.class_names[predicted_idx.item()], confidence.item() * 100, overlay_pil