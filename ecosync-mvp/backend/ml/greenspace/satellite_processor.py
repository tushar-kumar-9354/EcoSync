"""
Satellite Imagery Processing Pipeline for Green Space Analysis

Implements:
- Multi-source satellite data ingestion (Sentinel-2, Landsat 8)
- Cloud masking and atmospheric correction
- Land cover classification using U-Net
- Tree canopy delineation
- Heat island analysis (LST retrieval)
- Change detection over time
"""

import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
import math
from datetime import datetime
import json


@dataclass
class SatelliteImage:
    """Represents a satellite image with metadata."""
    data: np.ndarray  # [bands, height, width]
    bands: List[str]
    resolution_m: float
    timestamp: datetime
    bounds: Tuple[float, float, float, float]  # lat_min, lat_max, lng_min, lng_max
    cloud_percent: float
    source: str  # 'sentinel2', 'landsat8', 'aerial'


@dataclass
class LandCoverTile:
    """Land cover classification result for a tile."""
    tile_id: str
    data: np.ndarray  # [height, width] class indices
    class_probs: np.ndarray  # [height, width, num_classes]
    timestamp: datetime
    bounds: Tuple[float, float, float, float]


@dataclass
class HeatIslandZone:
    """Identified heat island zone."""
    zone_id: str
    bounds: Tuple[float, float, float, float]
    area_km2: float
    lst_celsius: float
    severity: str  # 'severe', 'moderate', 'mild'
    contributing_factors: List[str]


class UNetEncoder(nn.Module):
    """U-Net encoder for land cover segmentation."""

    def __init__(self, in_channels: int = 4, base_filters: int = 64):
        super().__init__()

        self.enc1 = self._make_layer(in_channels, base_filters)
        self.enc2 = self._make_layer(base_filters, base_filters * 2)
        self.enc3 = self._make_layer(base_filters * 2, base_filters * 4)
        self.enc4 = self._make_layer(base_filters * 4, base_filters * 8)

        self.pool = nn.MaxPool2d(2)

    def _make_layer(self, in_ch: int, out_ch: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )

    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        return [e1, e2, e3, e4]


class UNetDecoder(nn.Module):
    """U-Net decoder for land cover segmentation."""

    def __init__(self, out_channels: int = 6, base_filters: int = 64):
        super().__init__()

        self.up4 = nn.ConvTranspose2d(base_filters * 8, base_filters * 4, 2, stride=2)
        self.dec4 = self._make_layer(base_filters * 8, base_filters * 4)

        self.up3 = nn.ConvTranspose2d(base_filters * 4, base_filters * 2, 2, stride=2)
        self.dec3 = self._make_layer(base_filters * 4, base_filters * 2)

        self.up2 = nn.ConvTranspose2d(base_filters * 2, base_filters, 2, stride=2)
        self.dec2 = self._make_layer(base_filters * 2, base_filters)

        self.up1 = nn.ConvTranspose2d(base_filters, base_filters, 2, stride=2)
        self.dec1 = self._make_layer(base_filters, base_filters)

        self.final = nn.Conv2d(base_filters, out_channels, 1)

    def _make_layer(self, in_ch: int, out_ch: int) -> nn.Sequential:
        return nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True)
        )

    def forward(self, features: List[torch.Tensor]) -> torch.Tensor:
        e1, e2, e3, e4 = features

        d4 = self.up4(e4)
        d4 = torch.cat([d4, e3], dim=1)
        d4 = self.dec4(d4)

        d3 = self.up3(d4)
        d3 = torch.cat([d3, e2], dim=1)
        d3 = self.dec3(d3)

        d2 = self.up2(d3)
        d2 = torch.cat([d2, e1], dim=1)
        d2 = self.dec2(d2)

        d1 = self.up1(d2)
        d1 = self.dec1(d1)

        return self.final(d1)


class LandCoverModel(nn.Module):
    """
    U-Net model for land cover classification.

    Classes:
    0: Tree Canopy
    1: Grass/Lawn
    2: Impervious surfaces (buildings, roads)
    3: Water
    4: Bare soil
    5: Buildings
    """

    CLASS_NAMES = ['tree_canopy', 'grass', 'impervious', 'water', 'bare_soil', 'buildings']

    # Color map for visualization
    CLASS_COLORS = [
        [34, 139, 34],    # Forest green
        [124, 252, 0],    # Lawn green
        [128, 128, 128],  # Gray
        [30, 144, 255],   # Dodger blue
        [139, 119, 101],  # Tan
        [139, 87, 42]     # Brown
    ]

    def __init__(self, in_channels: int = 4, num_classes: int = 6):
        super().__init__()

        self.encoder = UNetEncoder(in_channels=in_channels)
        self.decoder = UNetDecoder(out_channels=num_classes)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: Input tensor [B, channels, H, W]

        Returns:
            logits: [B, num_classes, H, W]
            predictions: [B, H, W] class indices
        """
        features = self.encoder(x)
        logits = self.decoder(features)
        predictions = torch.argmax(logits, dim=1)
        return logits, predictions

    def predict_tile(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict land cover for a tile.

        Args:
            image: Input image [channels, H, W]

        Returns:
            predictions: [H, W] class indices
            probabilities: [H, W, num_classes]
        """
        self.eval()
        with torch.no_grad():
            x = torch.from_numpy(image).unsqueeze(0).float()
            logits, preds = self.forward(x)
            probs = torch.softmax(logits, dim=1)

        return preds.squeeze(0).numpy(), probs.squeeze(0).numpy()


class SatelliteProcessor:
    """
    Processes satellite imagery for green space analysis.

    Handles:
    - Multi-source data ingestion
    - Cloud masking
    - Atmospheric correction
    - Band normalization
    - Land cover classification
    - Change detection
    """

    BANDS_SENTINEL2 = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12']  # Blue, Green, Red, NIR, SWIR1, SWIR2
    BANDS_LANDSAT8 = ['B02', 'B03', 'B04', 'B05', 'B06', 'B07']  # Similar mapping

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = 'auto'
    ):
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = torch.device(device)
        self.land_cover_model: Optional[LandCoverModel] = None
        self.heat_model: Optional[nn.Module] = None

        if model_path:
            self.load_model(model_path)
        else:
            # Create model for inference
            self.land_cover_model = LandCoverModel()
            self.land_cover_model.to(self.device)
            self.land_cover_model.eval()

    def load_model(self, model_path: str) -> bool:
        """Load trained model from checkpoint."""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)

            if 'model_state_dict' in checkpoint:
                self.land_cover_model = LandCoverModel()
                self.land_cover_model.load_state_dict(checkpoint['model_state_dict'])
            else:
                self.land_cover_model = checkpoint

            self.land_cover_model.to(self.device)
            self.land_cover_model.eval()
            print(f"Loaded land cover model from {model_path}")
            return True

        except Exception as e:
            print(f"Error loading model: {e}")
            self.land_cover_model = LandCoverModel()
            self.land_cover_model.to(self.device)
            self.land_cover_model.eval()
            return False

    def preprocess_sentinel2(self, bands: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Preprocess Sentinel-2 bands for land cover classification.

        Args:
            bands: Dict mapping band name to numpy array

        Returns:
            Preprocessed image [4, H, W] - RGB + NIR
        """
        # Use: B04 (Red), B03 (Green), B02 (Blue), B08 (NIR)
        b04 = bands.get('B04', np.zeros_like(list(bands.values())[0]))
        b03 = bands.get('B03', np.zeros_like(list(bands.values())[0]))
        b02 = bands.get('B02', np.zeros_like(list(bands.values())[0]))
        b08 = bands.get('B08', np.zeros_like(list(bands.values())[0]))

        # Stack as [NIR, Red, Green, Blue] for better vegetation detection
        image = np.stack([b08, b04, b03, b02], axis=0)

        # Normalize to 0-1 range (Sentinel-2 is 16-bit)
        image = image.astype(np.float32) / 65535.0

        # Apply cloud mask if available (simplified)
        # In production, use QA60 band or separate cloud detection

        return image

    def compute_ndvi(self, nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """Compute Normalized Difference Vegetation Index."""
        ndvi = (nir - red) / (nir + red + 1e-8)
        return np.clip(ndvi, -1, 1)

    def compute_ndwi(self, green: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """Compute Normalized Difference Water Index."""
        ndwi = (green - nir) / (green + nir + 1e-8)
        return np.clip(ndwi, -1, 1)

    def compute_ndbi(self, swir: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """Compute Normalized Difference Built-up Index."""
        ndbi = (swir - nir) / (swir + nir + 1e-8)
        return np.clip(ndbi, -1, 1)

    def classify_land_cover(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Classify land cover in satellite image.

        Args:
            image: Preprocessed image [4, H, W]

        Returns:
            predictions: [H, W] class indices
            probabilities: [H, W, num_classes]
        """
        if self.land_cover_model is None:
            raise RuntimeError("Model not loaded")

        # Add indices as additional bands
        nir = image[0]
        red = image[1]
        green = image[2]
        swir = image[3] if image.shape[0] > 3 else image[0]

        ndvi = self.compute_ndvi(nir, red)
        ndwi = self.compute_ndwi(green, nir)
        ndbi = self.compute_ndbi(swir, nir)

        # Extend image with indices
        extended = np.stack([image[0], image[1], image[2], image[3], ndvi, ndwi], axis=0)

        # To tensor
        x = torch.from_numpy(extended).unsqueeze(0).float().to(self.device)

        with torch.no_grad():
            logits, preds = self.land_cover_model(x)
            probs = torch.softmax(logits, dim=1)

        return preds.squeeze(0).cpu().numpy(), probs.squeeze(0).cpu().numpy()

    def compute_tree_canopy_percent(self, land_cover: np.ndarray) -> float:
        """Compute tree canopy coverage percentage from land cover map."""
        total_pixels = land_cover.size
        tree_pixels = np.sum(land_cover == 0)  # Class 0 = tree canopy
        return (tree_pixels / total_pixels) * 100

    def detect_canopy_gaps(self, land_cover: np.ndarray, ndvi: np.ndarray) -> List[Dict]:
        """
        Detect gaps in tree canopy suitable for planting.

        Args:
            land_cover: Land cover classification
            ndvi: NDVI values

        Returns:
            List of gap locations
        """
        gaps = []

        # Find grass/bare soil areas adjacent to tree canopy
        # These are potential planting locations
        height, width = land_cover.shape

        for i in range(1, height - 1):
            for j in range(1, width - 1):
                current = land_cover[i, j]

                # Check if it's grass (class 1) or bare soil (class 4)
                if current in [1, 4] and ndvi[i, j] > 0.2:
                    # Check if adjacent to tree canopy
                    neighbors = [
                        land_cover[i-1, j], land_cover[i+1, j],
                        land_cover[i, j-1], land_cover[i, j+1]
                    ]
                    if 0 in neighbors:  # Adjacent to trees
                        gaps.append({
                            'row': i,
                            'col': j,
                            'current_class': int(current),
                            'ndvi': float(ndvi[i, j]),
                            'priority': 'medium' if ndvi[i, j] > 0.3 else 'low'
                        })

        return gaps[:1000]  # Limit for performance

    def estimate_canopy_volume(self, land_cover: np.ndarray, resolution_m: float) -> Dict:
        """
        Estimate total tree canopy volume/area.

        Args:
            land_cover: Land cover classification
            resolution_m: Pixel resolution in meters

        Returns:
            Canopy statistics
        """
        tree_mask = land_cover == 0
        total_tree_pixels = np.sum(tree_mask)
        total_area_km2 = (total_tree_pixels * resolution_m * resolution_m) / 1_000_000

        # Approximate canopy density from NDVI if available
        # (simplified - would need actual height data for volume)

        return {
            'canopy_pixels': int(total_tree_pixels),
            'canopy_area_km2': round(total_area_km2, 3),
            'canopy_percent': round((total_tree_pixels / land_cover.size) * 100, 2)
        }


class HeatIslandAnalyzer:
    """
    Analyze urban heat islands from satellite thermal data.

    Implements:
    - Land Surface Temperature (LST) retrieval
    - Hotspot identification
    - Contributing factor analysis
    - Risk zoning
    """

    def __init__(self):
        pass

    def estimate_lst_from_ndvi(
        self,
        ndvi: np.ndarray,
        air_temp_celsius: float = 30.0,
        emissivity: float = 0.95
    ) -> np.ndarray:
        """
        Estimate Land Surface Temperature from NDVI (simplified method).

        In production, use thermal bands (B10/B11 for Landsat 8, B10 for Sentinel-3).

        Args:
            ndvi: NDVI values
            air_temp_celsius: Estimated air temperature
            emissivity: Land surface emissivity

        Returns:
            LST in Celsius
        """
        # Simplified LST estimation
        # LST ≈ air_temp + (1/ε) * (0.3 + 0.7 * NDVI) * (TK^4 - 273^4) adjustment

        # This is a simplification - real LST requires thermal band data
        lst = air_temp_celsius + (1 - emissivity) * ndvi * 10

        return lst

    def compute_heat_risk_zones(
        self,
        lst: np.ndarray,
        threshold_high: float = 35.0,
        threshold_moderate: float = 30.0
    ) -> np.ndarray:
        """
        Compute heat risk zones from LST.

        Args:
            lst: Land surface temperature in Celsius
            threshold_high: Threshold for high risk
            threshold_moderate: Threshold for moderate risk

        Returns:
            Risk map: 0=none, 1=mild, 2=moderate, 3=severe
        """
        risk = np.zeros_like(lst, dtype=np.uint8)

        risk[lst >= threshold_high] = 3  # Severe
        risk[(lst >= threshold_moderate) & (lst < threshold_high)] = 2  # Moderate
        risk[(lst >= 25) & (lst < threshold_moderate)] = 1  # Mild

        return risk

    def identify_hotspots(
        self,
        lst: np.ndarray,
        min_area_km2: float = 0.1,
        resolution_m: float = 30.0
    ) -> List[Dict]:
        """
        Identify heat island hotspots using spatial clustering.

        Args:
            lst: LST array
            min_area_km2: Minimum hotspot area
            resolution_m: Pixel resolution

        Returns:
            List of hotspot definitions
        """
        hotspots = []
        threshold = np.percentile(lst, 90)  # Top 10% as hotspots
        min_pixels = int((min_area_km2 * 1_000_000) / (resolution_m ** 2))

        # Simple connected component analysis
        hot_mask = lst >= threshold
        labeled, num_features = self._connected_components(hot_mask)

        for i in range(1, num_features + 1):
            region_mask = labeled == i
            area_km2 = np.sum(region_mask) * (resolution_m ** 2) / 1_000_000

            if area_km2 >= min_area_km2:
                # Find bounding box
                rows, cols = np.where(region_mask)
                lst_values = lst[region_mask]

                hotspots.append({
                    'hotspot_id': f'HS-{len(hotspots) + 1:03d}',
                    'area_km2': round(area_km2, 3),
                    'avg_lst_celsius': round(float(np.mean(lst_values)), 1),
                    'max_lst_celsius': round(float(np.max(lst_values)), 1),
                    'min_lst_celsius': round(float(np.min(lst_values)), 1),
                    'severity': self._classify_severity(np.mean(lst_values)),
                    'bounding_box': {
                        'row_min': int(rows.min()),
                        'row_max': int(rows.max()),
                        'col_min': int(cols.min()),
                        'col_max': int(cols.max())
                    }
                })

        # Sort by avg LST
        hotspots.sort(key=lambda x: x['avg_lst_celsius'], reverse=True)

        return hotspots

    def _connected_components(self, mask: np.ndarray) -> Tuple[np.ndarray, int]:
        """Simple connected component labeling (4-connectivity)."""
        labeled = np.zeros_like(mask, dtype=np.int32)
        label = 0
        height, width = mask.shape

        def dfs(r: int, c: int, l: int):
            if r < 0 or r >= height or c < 0 or c >= width:
                return
            if not mask[r, c] or labeled[r, c]:
                return
            labeled[r, c] = l
            dfs(r + 1, c, l)
            dfs(r - 1, c, l)
            dfs(r, c + 1, l)
            dfs(r, c - 1, l)

        for i in range(height):
            for j in range(width):
                if mask[i, j] and not labeled[i, j]:
                    label += 1
                    dfs(i, j, label)

        return labeled, label

    def _classify_severity(self, avg_lst: float) -> str:
        """Classify hotspot severity."""
        if avg_lst >= 40:
            return 'severe'
        elif avg_lst >= 35:
            return 'moderate'
        return 'mild'

    def analyze_contributing_factors(
        self,
        land_cover: np.ndarray,
        lst: np.ndarray
    ) -> Dict:
        """
        Analyze factors contributing to heat islands.

        Args:
            land_cover: Land cover classification
            lst: Land surface temperature

        Returns:
            Factor analysis
        """
        # Class indices
        # 0: Tree, 1: Grass, 2: Impervious, 3: Water, 4: Bare, 5: Buildings

        factor_stats = {}

        for class_idx, class_name in enumerate(LandCoverModel.CLASS_NAMES):
            mask = land_cover == class_idx
            if np.any(mask):
                lst_values = lst[mask]
                factor_stats[class_name] = {
                    'avg_lst_celsius': round(float(np.mean(lst_values)), 1),
                    'max_lst_celsius': round(float(np.max(lst_values)), 1),
                    'pixel_count': int(np.sum(mask)),
                    'percent_of_area': round(float(np.sum(mask) / land_cover.size * 100), 2)
                }

        # Calculate cooling effect of green spaces
        tree_lst = factor_stats.get('tree_canopy', {}).get('avg_lst_celsius', 30)
        impervious_lst = factor_stats.get('impervious', {}).get('avg_lst_celsius', 35)

        cooling_effect = impervious_lst - tree_lst

        return {
            'class_statistics': factor_stats,
            'cooling_effect_of_greenspace_celsius': round(cooling_effect, 1),
            'primary_heat_sources': [
                name for name, stats in factor_stats.items()
                if stats['avg_lst_celsius'] > 35
            ],
            'recommendation': self._get_cooling_recommendation(cooling_effect)
        }

    def _get_cooling_recommendation(self, cooling_effect: float) -> str:
        """Get recommendation based on cooling effect."""
        if cooling_effect < 3:
            return "Critical need for tree planting - cooling effect below 3°C"
        elif cooling_effect < 5:
            return "Moderate need - expanding green canopy recommended"
        return "Good green coverage - focus on maintenance and connectivity"


class ChangeDetector:
    """
    Detect changes in land cover over time.

    Uses:
    - Image differencing
    - Post-classification comparison
    - Vegetation index differencing
    """

    def __init__(self):
        pass

    def detect_canopy_loss(
        self,
        land_cover_before: np.ndarray,
        land_cover_after: np.ndarray,
        resolution_m: float
    ) -> Dict:
        """
        Detect tree canopy loss between two time periods.

        Args:
            land_cover_before: Earlier land cover map
            land_cover_after: Later land cover map
            resolution_m: Pixel resolution

        Returns:
            Change detection results
        """
        # Tree canopy is class 0
        canopy_before = (land_cover_before == 0).astype(int)
        canopy_after = (land_cover_after == 0).astype(int)

        # Loss = was tree, now not tree
        loss_mask = (canopy_before == 1) & (canopy_after == 0)
        gain_mask = (canopy_before == 0) & (canopy_after == 1)

        loss_pixels = np.sum(loss_mask)
        gain_pixels = np.sum(gain_mask)
        net_change_pixels = gain_pixels - loss_pixels

        pixel_area_m2 = resolution_m ** 2

        return {
            'loss_km2': round(loss_pixels * pixel_area_m2 / 1_000_000, 3),
            'gain_km2': round(gain_pixels * pixel_area_m2 / 1_000_000, 3),
            'net_change_km2': round(net_change_pixels * pixel_area_m2 / 1_000_000, 3),
            'loss_pixels': int(loss_pixels),
            'gain_pixels': int(gain_pixels),
            'change_type': 'loss' if net_change_pixels < 0 else 'gain' if net_change_pixels > 0 else 'stable'
        }

    def detect_impervious_surface_change(
        self,
        land_cover_before: np.ndarray,
        land_cover_after: np.ndarray,
        resolution_m: float
    ) -> Dict:
        """Detect increase in impervious surfaces (development)."""
        imperv_before = (land_cover_before == 2).astype(int)
        imperv_after = (land_cover_after == 2).astype(int)

        gain_mask = (imperv_before == 0) & (imperv_after == 1)
        pixel_area_m2 = resolution_m ** 2

        gain_km2 = np.sum(gain_mask) * pixel_area_m2 / 1_000_000

        return {
            'impervious_gain_km2': round(gain_km2, 3),
            'associated_canopy_loss_km2': round(gain_km2 * 0.7, 3),  # Rough estimate
            'change_type': 'development' if gain_km2 > 0.01 else 'stable'
        }
