from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class AudioFeatures:
    """Class to store audio features extracted from a sample."""
    spectral_centroid: float = 0.0
    spectral_bandwidth: float = 0.0
    spectral_rolloff: float = 0.0
    zero_crossing_rate: float = 0.0
    mfcc: List[float] = field(default_factory=list)
    chroma: List[float] = field(default_factory=list)
    energy: float = 0.0
    tempo: float = 0.0
    duration: float = 0.0
    rms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert features to dictionary for JSON serialization."""
        return {
            'spectral_centroid': self.spectral_centroid,
            'spectral_bandwidth': self.spectral_bandwidth,
            'spectral_rolloff': self.spectral_rolloff,
            'zero_crossing_rate': self.zero_crossing_rate,
            'mfcc': self.mfcc[:5],  # Only include first 5 MFCC coefficients for simplicity
            'chroma': self.chroma[:5],  # Only include first 5 chroma features for simplicity
            'energy': self.energy,
            'tempo': self.tempo,
            'duration': self.duration,
            'rms': self.rms
        }

@dataclass
class AudioSample:
    """Class to represent an audio sample."""
    id: str
    name: str
    path: str
    features: Optional[AudioFeatures] = None
    category: str = "Unknown"
    mood: str = "Unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sample to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'path': self.path,
            'features': self.features.to_dict() if self.features else {},
            'category': self.category,
            'mood': self.mood
        }
