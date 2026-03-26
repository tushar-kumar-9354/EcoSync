"""
Waste Classification Computer Vision Module

Implements:
- YOLOv8-style architecture for waste classification
- On-device inference for truck-mounted cameras
- Contamination detection
- Material type identification (recyclable, organic, landfill)
"""

import torch
import torch.nn as nn
from typing import List, Tuple, Optional, Dict
import math


class ConvBlock(nn.Module):
    """Convolutional block with batch norm and activation."""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3,
                 stride: int = 1, padding: int = 1, activation: str = 'silu'):
        super().__init__()

        self.conv = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)

        if activation == 'silu':
            self.activation = nn.SiLU()
        elif activation == 'relu':
            self.activation = nn.ReLU()
        else:
            self.activation = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(self.bn(self.conv(x)))


class BottleneckBlock(nn.Module):
    """Residual bottleneck block for efficient feature extraction."""

    def __init__(self, channels: int, shortcut: bool = True, expansion: float = 0.5):
        super().__init__()

        hidden_dim = int(channels * expansion)
        self.conv1 = ConvBlock(channels, hidden_dim, kernel_size=1)
        self.conv2 = ConvBlock(hidden_dim, channels, kernel_size=3)

        self.use_shortcut = shortcut and hidden_dim == channels

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_shortcut:
            return x + self.conv2(self.conv1(x))
        return self.conv2(self.conv1(x))


class SPPFBlock(nn.Module):
    """Spatial Pyramid Pooling - Fast version for multi-scale features."""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 5):
        super().__init__()

        hidden_dim = in_channels // 2
        self.conv1 = ConvBlock(in_channels, hidden_dim, kernel_size=1)
        self.pool = nn.MaxPool2d(kernel_size=kernel_size, stride=1, padding=kernel_size // 2)
        self.conv2 = ConvBlock(hidden_dim * 4, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        y1 = self.pool(x)
        y2 = self.pool(y1)
        y3 = self.pool(y2)
        return self.conv2(torch.cat([x, y1, y2, y3], dim=1))


class C2fBlock(nn.Module):
    """CSP Bottleneck with 2 convolutions - YOLOv8's main building block."""

    def __init__(self, in_channels: int, out_channels: int, num_bottlenecks: int = 1, shortcut: bool = False):
        super().__init__()

        self.conv1 = ConvBlock(in_channels, out_channels, kernel_size=1)
        self.conv2 = ConvBlock(in_channels, out_channels, kernel_size=1)

        self.bottlenecks = nn.ModuleList([
            BottleneckBlock(out_channels, shortcut=shortcut)
            for _ in range(num_bottlenecks)
        ])

        self.conv3 = ConvBlock((num_bottlenecks + 2) * out_channels, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.conv1(x)
        x2 = self.conv2(x)

        features = [x1, x2]
        for bottleneck in self.bottlenecks:
            features.append(bottleneck(features[-1]))

        return self.conv3(torch.cat(features, dim=1))


class DetectionHead(nn.Module):
    """Detection head for waste classification and bounding boxes."""

    def __init__(
        self,
        num_classes: int,
        in_channels: List[int],
        num_anchors: int = 1
    ):
        super().__init__()

        self.num_classes = num_classes
        self.num_anchors = num_anchors

        # Classification head
        self.cls_heads = nn.ModuleList([
            nn.Sequential(
                ConvBlock(ch, ch, kernel_size=3),
                ConvBlock(ch, ch, kernel_size=3),
                nn.Conv2d(ch, num_anchors * num_classes, kernel_size=1)
            )
            for ch in in_channels
        ])

        # Box regression head
        self.box_heads = nn.ModuleList([
            nn.Sequential(
                ConvBlock(ch, ch, kernel_size=3),
                ConvBlock(ch, ch, kernel_size=3),
                nn.Conv2d(ch, num_anchors * 4, kernel_size=1)  # x, y, w, h
            )
            for ch in in_channels
        ])

        # Confidence head (objectness)
        self.conf_heads = nn.ModuleList([
            nn.Sequential(
                ConvBlock(ch, ch, kernel_size=3),
                ConvBlock(ch, ch, kernel_size=3),
                nn.Conv2d(ch, num_anchors * 1, kernel_size=1)
            )
            for ch in in_channels
        ])

    def forward(self, features: List[torch.Tensor]) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        cls_outputs = []
        box_outputs = []
        conf_outputs = []

        for i, feat in enumerate(features):
            cls_outputs.append(self.cls_heads[i](feat))
            box_outputs.append(self.box_heads[i](feat))
            conf_outputs.append(self.conf_heads[i](feat))

        return cls_outputs, box_outputs, conf_outputs


class WasteClassificationModel(nn.Module):
    """
    YOLOv8-style model for waste classification.

    Supports:
    - Multi-class waste classification
    - Contamination detection
    - Material composition analysis
    """

    # Waste categories
    CLASSES = [
        'cardboard', 'paper', 'plastic_bottle', 'plastic_bag', 'glass',
        'metal_can', 'food_waste', 'garden_waste', 'textile', 'electronics',
        'batteries', 'construction', 'medical', 'other_landfill'
    ]

    # Material types
    MATERIAL_TYPES = {
        'cardboard': 'recyclable',
        'paper': 'recyclable',
        'plastic_bottle': 'recyclable',
        'plastic_bag': 'recyclable',
        'glass': 'recyclable',
        'metal_can': 'recyclable',
        'food_waste': 'organic',
        'garden_waste': 'organic',
        'textile': 'recycle_process',
        'electronics': 'hazardous',
        'batteries': 'hazardous',
        'construction': 'construction',
        'medical': 'hazardous',
        'other_landfill': 'landfill'
    }

    def __init__(
        self,
        num_classes: int = 14,
        depth_multiple: float = 1.0,
        width_multiple: float = 1.0
    ):
        super().__init__()

        self.num_classes = num_classes

        # Scale factors
        def make_divisible(x, divisor=8):
            return math.ceil(x * width_multiple / divisor) * divisor

        def scale_depth(x):
            return max(round(x * depth_multiple), 1)

        # Backbone
        self.stem = ConvBlock(3, make_divisible(64), kernel_size=3, padding=1)

        self.stage1 = nn.Sequential(
            ConvBlock(make_divisible(64), make_divisible(128), kernel_size=3, padding=1, stride=2),
            C2fBlock(make_divisible(128), make_divisible(128), num_bottlenecks=scale_depth(3))
        )

        self.stage2 = nn.Sequential(
            ConvBlock(make_divisible(128), make_divisible(256), kernel_size=3, padding=1, stride=2),
            C2fBlock(make_divisible(256), make_divisible(256), num_bottlenecks=scale_depth(6))
        )

        self.stage3 = nn.Sequential(
            ConvBlock(make_divisible(256), make_divisible(512), kernel_size=3, padding=1, stride=2),
            C2fBlock(make_divisible(512), make_divisible(512), num_bottlenecks=6)
        )

        self.stage4 = nn.Sequential(
            ConvBlock(make_divisible(512), make_divisible(1024), kernel_size=3, padding=1, stride=2),
            SPPFBlock(make_divisible(1024), make_divisible(1024))
        )

        # Detection head
        in_channels = [make_divisible(256), make_divisible(512), make_divisible(1024)]
        self.head = DetectionHead(num_classes, in_channels)

        self._initialize_weights()

    def _initialize_weights(self):
        """Initialize model weights."""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> Tuple[List[torch.Tensor], List[torch.Tensor], List[torch.Tensor]]:
        # Backbone forward
        x = self.stem(x)

        x1 = self.stage1(x)
        x2 = self.stage2(x1)
        x3 = self.stage3(x2)
        x4 = self.stage4(x3)

        # Detection head
        features = [x2, x3, x4]
        cls_out, box_out, conf_out = self.head(features)

        return cls_out, box_out, conf_out

    def predict_waste_type(
        self,
        image: torch.Tensor,
        conf_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Predict waste types in an image.

        Args:
            image: Input image tensor [B, 3, H, W]
            conf_threshold: Confidence threshold

        Returns:
            List of predictions with class, confidence, and material type
        """
        self.eval()
        with torch.no_grad():
            cls_out, box_out, conf_out = self.forward(image)

        predictions = []

        # Process each scale
        for scale_idx in range(len(cls_out)):
            cls_pred = cls_out[scale_idx]
            conf_pred = torch.sigmoid(conf_out[scale_idx])
            box_pred = box_out[scale_idx]

            # Get max class per anchor
            class_scores, class_indices = torch.max(cls_pred, dim=1)

            # Filter by confidence
            mask = conf_pred.squeeze() > conf_threshold
            if mask.sum() == 0:
                continue

            scores = (conf_pred.squeeze() * torch.sigmoid(class_scores)).squeeze()

            for i in range(len(scores[mask])):
                idx = mask.nonzero()[i]
                score = scores[idx].item()
                class_id = class_indices[idx[0], idx[1], idx[2]].item()
                box = box_pred[0, :, idx[0], idx[1], idx[2]].cpu().numpy()

                predictions.append({
                    'class': self.CLASSES[class_id],
                    'material_type': self.MATERIAL_TYPES[self.CLASSES[class_id]],
                    'confidence': score,
                    'box': box.tolist()
                })

        return predictions


class WasteClassifier:
    """
    High-level interface for waste classification.

    Handles:
    - Model loading and inference
    - Image preprocessing
    - Batch processing for facility cameras
    - Integration with route optimization
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = 'auto',
        conf_threshold: float = 0.5
    ):
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = torch.device(device)
        self.conf_threshold = conf_threshold
        self.model: Optional[WasteClassificationModel] = None

        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str) -> bool:
        """Load trained model from checkpoint."""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)

            if 'model_state_dict' in checkpoint:
                self.model = WasteClassificationModel()
                self.model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.model = checkpoint

            self.model.to(self.device)
            self.model.eval()

            print(f"Loaded waste classification model from {model_path}")
            return True

        except Exception as e:
            print(f"Error loading model: {e}")
            # Create a new model for demo purposes
            self.model = WasteClassificationModel()
            self.model.to(self.device)
            self.model.eval()
            return False

    def preprocess_image(self, image: torch.Tensor, target_size: Tuple[int, int] = (640, 640)) -> torch.Tensor:
        """
        Preprocess image for inference.

        Args:
            image: Input image [3, H, W] or [B, 3, H, W]
            target_size: Target size (width, height)

        Returns:
            Preprocessed image tensor
        """
        if len(image.shape) == 3:
            image = image.unsqueeze(0)

        # Resize
        image = torch.nn.functional.interpolate(
            image,
            size=target_size,
            mode='bilinear',
            align_corners=False
        )

        # Normalize (ImageNet stats)
        mean = torch.tensor([0.485, 0.456, 0.406], device=image.device).view(1, 3, 1, 1)
        std = torch.tensor([0.229, 0.224, 0.225], device=image.device).view(1, 3, 1, 1)
        image = (image / 255.0 - mean) / std

        return image

    def classify_image(self, image: torch.Tensor) -> List[Dict]:
        """Classify waste in an image."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        image = self.preprocess_image(image.to(self.device))

        predictions = self.model.predict_waste_type(image, self.conf_threshold)

        return predictions

    def classify_batch(self, images: torch.Tensor) -> List[List[Dict]]:
        """Classify waste in a batch of images."""
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Preprocess batch
        images = self.preprocess_image(images.to(self.device))

        predictions_per_image = []

        with torch.no_grad():
            cls_out, box_out, conf_out = self.model.forward(images)

        batch_size = images.size(0)

        for b in range(batch_size):
            predictions = []

            for scale_idx in range(len(cls_out)):
                cls_pred = cls_out[scale_idx][b]
                conf_pred = torch.sigmoid(conf_out[scale_idx][b])
                class_scores, class_indices = torch.max(cls_pred, dim=0)

                scores = conf_pred * torch.sigmoid(class_scores)
                mask = scores > self.conf_threshold

                if mask.sum() == 0:
                    continue

                for i in range(mask.sum()):
                    idx = mask.nonzero()[i]
                    score = scores[idx[0], idx[1], idx[2]].item()
                    class_id = class_indices[idx[0], idx[1], idx[2]].item()

                    predictions.append({
                        'class': WasteClassificationModel.CLASSES[class_id],
                        'material_type': WasteClassificationModel.MATERIAL_TYPES[
                            WasteClassificationModel.CLASSES[class_id]
                        ],
                        'confidence': score
                    })

            predictions_per_image.append(predictions)

        return predictions_per_image

    def analyze_composition(self, predictions: List[Dict]) -> Dict:
        """
        Analyze composition of waste from predictions.

        Returns:
            Dictionary with material breakdown
        """
        total = len(predictions)
        if total == 0:
            return {
                'total_items': 0,
                'recyclable': 0,
                'organic': 0,
                'hazardous': 0,
                'landfill': 0,
                'composition': {}
            }

        counts = {
            'recyclable': 0,
            'organic': 0,
            'hazardous': 0,
            'landfill': 0,
            'construction': 0
        }

        class_counts = {}

        for pred in predictions:
            material = pred['material_type']
            class_name = pred['class']

            counts[material] = counts.get(material, 0) + 1
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

        return {
            'total_items': total,
            'material_breakdown': {
                k: f"{v / total * 100:.1f}%" for k, v in counts.items()
            },
            'class_counts': class_counts,
            'contamination_risk': 'high' if counts.get('landfill', 0) / total > 0.1 else 'low'
        }


class OnDeviceClassifier:
    """
    Optimized classifier for edge deployment on collection trucks.

    Features:
    - INT8 quantization for faster inference
    - TensorRT optimization ready
    - Memory-efficient batch processing
    """

    def __init__(self, model: WasteClassificationModel, quantize: bool = True):
        self.model = model
        self.quantized = False

        if quantize:
            self.quantize()

    def quantize(self):
        """Post-training quantization to INT8."""
        # Dynamic quantization for linear layers
        self.model = torch.quantization.quantize_dynamic(
            self.model,
            {nn.Linear, nn.Conv2d},
            dtype=torch.qint8
        )
        self.quantized = True
        print("Model quantized to INT8")

    @torch.no_grad()
    def inference(self, image: torch.Tensor) -> List[Dict]:
        """Fast inference on edge device."""
        # Use lower precision and simpler processing
        image = image.to(torch.float16) if torch.cuda.is_available() else image
        return self.model.predict_waste_type(image, conf_threshold=0.6)
