"""
Visual effects overlay for Napoleon Total War.
A custom ReShade-style overlay with 54 visual effects organized in categories,
featuring sliders, color pickers, and preset management.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QApplication,
        QScrollArea, QSlider, QFrame, QComboBox, QPushButton,
        QColorDialog, QCheckBox, QGroupBox, QGridLayout,
        QGraphicsOpacityEffect, QTabWidget, QSizePolicy,
    )
    from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

logger = logging.getLogger('napoleon.effects_overlay')


# ══════════════════════════════════════════════════════════════
# Effect Categories
# ══════════════════════════════════════════════════════════════

class EffectCategory(Enum):
    """Categories for visual effects."""
    COLOR = "color"
    LIGHTING = "lighting"
    BLUR_FOCUS = "blur_focus"
    CINEMATIC = "cinematic"
    ATMOSPHERE = "atmosphere"
    FILM_GRAIN_NOISE = "film_grain_noise"
    ARTISTIC = "artistic"
    NAPOLEON_THEMED = "napoleon_themed"

    @classmethod
    def display_names(cls) -> Dict[str, str]:
        """Return mapping of enum values to user-friendly display names."""
        return {
            cls.COLOR.value: "🎨 Color",
            cls.LIGHTING.value: "💡 Lighting",
            cls.BLUR_FOCUS.value: "🔍 Blur & Focus",
            cls.CINEMATIC.value: "🎬 Cinematic",
            cls.ATMOSPHERE.value: "🌫️ Atmosphere",
            cls.FILM_GRAIN_NOISE.value: "📷 Film Grain & Noise",
            cls.ARTISTIC.value: "🖌️ Artistic",
            cls.NAPOLEON_THEMED.value: "⚔️ Napoleon Themed",
        }


# ══════════════════════════════════════════════════════════════
# Effect Definition
# ══════════════════════════════════════════════════════════════

@dataclass
class EffectParameter:
    """A single adjustable parameter of an effect."""
    name: str
    param_type: str  # "slider", "color", "toggle"
    default_value: Any
    min_value: float = 0.0
    max_value: float = 100.0
    step: float = 1.0
    suffix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EffectParameter':
        return cls(**data)


@dataclass
class EffectDefinition:
    """Definition of a single visual effect."""
    effect_id: str
    name: str
    category: str
    description: str
    parameters: List[EffectParameter] = field(default_factory=list)
    enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EffectDefinition':
        params = [EffectParameter.from_dict(p) for p in data.get('parameters', [])]
        return cls(
            effect_id=data['effect_id'],
            name=data['name'],
            category=data['category'],
            description=data['description'],
            parameters=params,
            enabled=data.get('enabled', False),
        )


@dataclass
class EffectState:
    """Runtime state of a single effect (enabled flag + parameter values)."""
    enabled: bool = False
    values: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {'enabled': self.enabled, 'values': dict(self.values)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EffectState':
        return cls(enabled=data.get('enabled', False),
                   values=dict(data.get('values', {})))


@dataclass
class EffectsPreset:
    """A named preset containing the state of all effects."""
    name: str
    description: str = ""
    effects: Dict[str, EffectState] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'effects': {k: v.to_dict() for k, v in self.effects.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EffectsPreset':
        effects = {}
        for eid, state_data in data.get('effects', {}).items():
            effects[eid] = EffectState.from_dict(state_data)
        return cls(
            name=data.get('name', 'Unnamed'),
            description=data.get('description', ''),
            effects=effects,
        )


# ══════════════════════════════════════════════════════════════
# Effect Registry — 50+ effects across 8 categories
# ══════════════════════════════════════════════════════════════

def _slider(name: str, default: float = 50.0, min_v: float = 0.0,
            max_v: float = 100.0, step: float = 1.0,
            suffix: str = "%") -> EffectParameter:
    return EffectParameter(name, "slider", default, min_v, max_v, step, suffix)


def _color(name: str, default: str = "#ffffff") -> EffectParameter:
    return EffectParameter(name, "color", default)


def _toggle(name: str, default: bool = False) -> EffectParameter:
    return EffectParameter(name, "toggle", default)


def _build_effect(effect_id: str, name: str, category: str,
                  description: str,
                  parameters: List[EffectParameter]) -> EffectDefinition:
    return EffectDefinition(
        effect_id=effect_id,
        name=name,
        category=category,
        description=description,
        parameters=parameters,
    )


def build_default_effects() -> List[EffectDefinition]:
    """Build and return the full registry of all default effects."""
    cat = EffectCategory
    effects: List[EffectDefinition] = []

    # ── COLOR (8 effects) ─────────────────────────────────────
    effects.append(_build_effect(
        "vibrance", "Vibrance", cat.COLOR.value,
        "Boost colour saturation of muted tones while protecting skin tones",
        [_slider("Intensity", 50), _color("Tint Color", "#ffffff")],
    ))
    effects.append(_build_effect(
        "saturation", "Saturation", cat.COLOR.value,
        "Global saturation adjustment for the entire scene",
        [_slider("Amount", 50, -100, 100), _toggle("Preserve Luminance")],
    ))
    effects.append(_build_effect(
        "color_balance", "Color Balance", cat.COLOR.value,
        "Shift shadows, midtones and highlights toward a chosen colour",
        [_slider("Shadows", 50), _slider("Midtones", 50),
         _slider("Highlights", 50),
         _color("Shadow Tint", "#003366"),
         _color("Highlight Tint", "#ffcc00")],
    ))
    effects.append(_build_effect(
        "hue_shift", "Hue Shift", cat.COLOR.value,
        "Rotate the entire colour wheel by a given angle",
        [_slider("Angle", 0, 0, 360, 1, "°")],
    ))
    effects.append(_build_effect(
        "color_grading", "Color Grading (LUT)", cat.COLOR.value,
        "Apply a colour lookup table for cinematic grading",
        [_slider("Intensity", 75), _color("Lift", "#000000"),
         _color("Gamma", "#808080"), _color("Gain", "#ffffff")],
    ))
    effects.append(_build_effect(
        "selective_color", "Selective Color", cat.COLOR.value,
        "Adjust individual colour channels independently",
        [_slider("Red", 50), _slider("Orange", 50), _slider("Yellow", 50),
         _slider("Green", 50), _slider("Cyan", 50), _slider("Blue", 50)],
    ))
    effects.append(_build_effect(
        "sepia_tone", "Sepia Tone", cat.COLOR.value,
        "Apply a warm brownish sepia filter for an antique look",
        [_slider("Intensity", 60), _color("Tone Color", "#704214")],
    ))
    effects.append(_build_effect(
        "split_toning", "Split Toning", cat.COLOR.value,
        "Apply different colour tints to shadows and highlights",
        [_color("Shadow Color", "#1a237e"), _color("Highlight Color", "#ff8f00"),
         _slider("Balance", 50)],
    ))

    # ── LIGHTING (7 effects) ──────────────────────────────────
    effects.append(_build_effect(
        "brightness", "Brightness", cat.LIGHTING.value,
        "Adjust overall scene brightness",
        [_slider("Level", 50, 0, 100)],
    ))
    effects.append(_build_effect(
        "contrast", "Contrast", cat.LIGHTING.value,
        "Adjust tonal range between darks and lights",
        [_slider("Amount", 50, 0, 100)],
    ))
    effects.append(_build_effect(
        "exposure", "Exposure", cat.LIGHTING.value,
        "Simulate camera exposure adjustment",
        [_slider("EV", 0, -5, 5, 0.1, " EV")],
    ))
    effects.append(_build_effect(
        "gamma", "Gamma Correction", cat.LIGHTING.value,
        "Non-linear brightness curve adjustment",
        [_slider("Gamma", 1.0, 0.1, 3.0, 0.01, "")],
    ))
    effects.append(_build_effect(
        "levels", "Levels", cat.LIGHTING.value,
        "Fine-tune shadow, midtone and highlight mapping",
        [_slider("Black Point", 0), _slider("Midpoint", 50),
         _slider("White Point", 100)],
    ))
    effects.append(_build_effect(
        "tonemapping", "Tone Mapping (HDR)", cat.LIGHTING.value,
        "Compress dynamic range for a richer image",
        [_slider("Strength", 50), _slider("Adaptation", 50),
         _toggle("Auto Exposure")],
    ))
    effects.append(_build_effect(
        "bloom", "Bloom", cat.LIGHTING.value,
        "Add a soft glow around bright areas",
        [_slider("Intensity", 30), _slider("Threshold", 70),
         _slider("Radius", 40), _color("Bloom Tint", "#ffffff")],
    ))

    # ── BLUR & FOCUS (6 effects) ──────────────────────────────
    effects.append(_build_effect(
        "depth_of_field", "Depth of Field", cat.BLUR_FOCUS.value,
        "Simulate lens blur on foreground/background",
        [_slider("Focus Distance", 50), _slider("Aperture", 40),
         _slider("Blur Strength", 30), _toggle("Auto Focus")],
    ))
    effects.append(_build_effect(
        "gaussian_blur", "Gaussian Blur", cat.BLUR_FOCUS.value,
        "Apply a smooth gaussian blur across the image",
        [_slider("Radius", 5, 0, 50)],
    ))
    effects.append(_build_effect(
        "motion_blur", "Motion Blur", cat.BLUR_FOCUS.value,
        "Simulate camera motion blur for a sense of speed",
        [_slider("Strength", 20), _slider("Angle", 0, 0, 360, 1, "°")],
    ))
    effects.append(_build_effect(
        "tilt_shift", "Tilt Shift", cat.BLUR_FOCUS.value,
        "Miniature/diorama effect with selective focus band",
        [_slider("Focus Position", 50), _slider("Focus Width", 30),
         _slider("Blur Amount", 40)],
    ))
    effects.append(_build_effect(
        "radial_blur", "Radial Blur", cat.BLUR_FOCUS.value,
        "Circular blur radiating from the centre of the screen",
        [_slider("Strength", 20), _slider("Center X", 50),
         _slider("Center Y", 50)],
    ))
    effects.append(_build_effect(
        "sharpen", "Sharpen", cat.BLUR_FOCUS.value,
        "Enhance edge detail and clarity",
        [_slider("Amount", 30), _slider("Radius", 1, 0, 10, 0.1, "px")],
    ))

    # ── CINEMATIC (7 effects) ─────────────────────────────────
    effects.append(_build_effect(
        "vignette", "Vignette", cat.CINEMATIC.value,
        "Darken or tint the edges of the screen",
        [_slider("Intensity", 40), _slider("Radius", 60),
         _slider("Softness", 70), _color("Vignette Color", "#000000")],
    ))
    effects.append(_build_effect(
        "letterbox", "Letterbox (Cinematic Bars)", cat.CINEMATIC.value,
        "Add horizontal black bars for a widescreen cinema look",
        [_slider("Bar Size", 10, 0, 30, 1, "%"),
         _color("Bar Color", "#000000")],
    ))
    effects.append(_build_effect(
        "chromatic_aberration", "Chromatic Aberration", cat.CINEMATIC.value,
        "Simulate lens colour fringing at the edges",
        [_slider("Intensity", 15), _slider("Offset", 2, 0, 20, 0.5, "px")],
    ))
    effects.append(_build_effect(
        "lens_distortion", "Lens Distortion", cat.CINEMATIC.value,
        "Apply barrel or pincushion distortion",
        [_slider("Amount", 0, -50, 50), _toggle("Barrel Mode")],
    ))
    effects.append(_build_effect(
        "anamorphic_flare", "Anamorphic Lens Flare", cat.CINEMATIC.value,
        "Horizontal streak flares from bright light sources",
        [_slider("Intensity", 30), _slider("Streak Length", 50),
         _color("Flare Color", "#89cff0")],
    ))
    effects.append(_build_effect(
        "film_borders", "Film Borders", cat.CINEMATIC.value,
        "Add decorative film-strip borders around the viewport",
        [_slider("Width", 5, 0, 20), _color("Border Color", "#1a1a1a"),
         _toggle("Rounded Corners")],
    ))
    effects.append(_build_effect(
        "color_fade", "Color Fade / Flash", cat.CINEMATIC.value,
        "Overlay a solid colour fade across the screen",
        [_slider("Opacity", 0), _color("Fade Color", "#000000")],
    ))

    # ── ATMOSPHERE (7 effects) ────────────────────────────────
    effects.append(_build_effect(
        "fog", "Fog / Mist", cat.ATMOSPHERE.value,
        "Add atmospheric depth fog",
        [_slider("Density", 30), _slider("Start Distance", 20),
         _color("Fog Color", "#c8c8c8")],
    ))
    effects.append(_build_effect(
        "light_rays", "God Rays (Light Shafts)", cat.ATMOSPHERE.value,
        "Volumetric light beams streaming from the sun",
        [_slider("Intensity", 40), _slider("Decay", 60),
         _color("Ray Color", "#fff5cc")],
    ))
    effects.append(_build_effect(
        "ambient_light", "Ambient Light", cat.ATMOSPHERE.value,
        "Add a soft coloured ambient glow to the scene",
        [_slider("Intensity", 25), _color("Light Color", "#ffeedd")],
    ))
    effects.append(_build_effect(
        "lens_dirt", "Lens Dirt", cat.ATMOSPHERE.value,
        "Simulate dirty lens with scattered light spots",
        [_slider("Intensity", 20), _slider("Spot Size", 40)],
    ))
    effects.append(_build_effect(
        "rain_drops", "Rain Drops", cat.ATMOSPHERE.value,
        "Simulate rain drops on the camera lens",
        [_slider("Intensity", 30), _slider("Drop Size", 40),
         _slider("Speed", 50)],
    ))
    effects.append(_build_effect(
        "heat_haze", "Heat Haze", cat.ATMOSPHERE.value,
        "Shimmering heat distortion rising from the ground",
        [_slider("Intensity", 20), _slider("Speed", 30)],
    ))
    effects.append(_build_effect(
        "dust_particles", "Dust Particles", cat.ATMOSPHERE.value,
        "Floating dust motes catching light",
        [_slider("Density", 30), _slider("Size", 40),
         _color("Particle Color", "#ffe8b0")],
    ))

    # ── FILM GRAIN & NOISE (5 effects) ────────────────────────
    effects.append(_build_effect(
        "film_grain", "Film Grain", cat.FILM_GRAIN_NOISE.value,
        "Add classic analogue film grain texture",
        [_slider("Intensity", 20), _slider("Size", 40),
         _toggle("Coloured Grain")],
    ))
    effects.append(_build_effect(
        "noise", "Digital Noise", cat.FILM_GRAIN_NOISE.value,
        "Add subtle digital sensor noise",
        [_slider("Amount", 15), _toggle("Uniform Noise")],
    ))
    effects.append(_build_effect(
        "scanlines", "CRT Scanlines", cat.FILM_GRAIN_NOISE.value,
        "Retro CRT monitor scanline overlay",
        [_slider("Intensity", 20), _slider("Line Width", 2, 1, 10, 1, "px"),
         _toggle("Interlaced")],
    ))
    effects.append(_build_effect(
        "halftone", "Halftone", cat.FILM_GRAIN_NOISE.value,
        "Newspaper-style dot pattern overlay",
        [_slider("Dot Size", 30), _slider("Angle", 45, 0, 90, 1, "°"),
         _color("Dot Color", "#000000")],
    ))
    effects.append(_build_effect(
        "dithering", "Dithering", cat.FILM_GRAIN_NOISE.value,
        "Ordered dithering for a retro banding reduction look",
        [_slider("Strength", 20), _slider("Pattern Size", 4, 2, 16, 2, "px")],
    ))

    # ── ARTISTIC (6 effects) ──────────────────────────────────
    effects.append(_build_effect(
        "posterize", "Posterize", cat.ARTISTIC.value,
        "Reduce colour levels for a poster / pop-art look",
        [_slider("Levels", 8, 2, 32, 1, "")],
    ))
    effects.append(_build_effect(
        "cel_shading", "Cel Shading", cat.ARTISTIC.value,
        "Cartoon outline and flat shading effect",
        [_slider("Edge Thickness", 30), _slider("Shading Steps", 4, 2, 12, 1, ""),
         _color("Edge Color", "#000000")],
    ))
    effects.append(_build_effect(
        "sketch", "Pencil Sketch", cat.ARTISTIC.value,
        "Convert the scene to a pencil sketch style",
        [_slider("Detail", 50), _slider("Brightness", 60),
         _toggle("Coloured Sketch")],
    ))
    effects.append(_build_effect(
        "pixelate", "Pixelate", cat.ARTISTIC.value,
        "Reduce resolution in blocks for a retro pixel look",
        [_slider("Block Size", 4, 1, 32, 1, "px")],
    ))
    effects.append(_build_effect(
        "emboss", "Emboss", cat.ARTISTIC.value,
        "Create a raised relief embossed look",
        [_slider("Strength", 40), _slider("Angle", 135, 0, 360, 1, "°")],
    ))
    effects.append(_build_effect(
        "oil_painting", "Oil Painting", cat.ARTISTIC.value,
        "Simulate oil-painting brush strokes",
        [_slider("Brush Size", 4, 1, 16, 1, "px"),
         _slider("Smoothness", 50)],
    ))

    # ── NAPOLEON THEMED (8 effects) ───────────────────────────
    effects.append(_build_effect(
        "battle_smoke", "Battle Smoke", cat.NAPOLEON_THEMED.value,
        "Thick black-powder smoke drifting across the battlefield",
        [_slider("Density", 40), _slider("Drift Speed", 30),
         _color("Smoke Color", "#8b8378")],
    ))
    effects.append(_build_effect(
        "cannon_flash", "Cannon Flash", cat.NAPOLEON_THEMED.value,
        "Bright muzzle flash pulses from cannon fire",
        [_slider("Intensity", 35), _slider("Frequency", 20),
         _color("Flash Color", "#fff176")],
    ))
    effects.append(_build_effect(
        "imperial_gold", "Imperial Gold", cat.NAPOLEON_THEMED.value,
        "Golden hue inspired by Napoleon's Imperial colour palette",
        [_slider("Intensity", 40), _color("Gold Tint", "#d4af37")],
    ))
    effects.append(_build_effect(
        "old_map", "Old Map Parchment", cat.NAPOLEON_THEMED.value,
        "Parchment-coloured overlay with aged paper texture feel",
        [_slider("Intensity", 30), _color("Parchment Color", "#f5deb3"),
         _slider("Edge Burn", 40)],
    ))
    effects.append(_build_effect(
        "winter_campaign", "Winter Campaign", cat.NAPOLEON_THEMED.value,
        "Cold desaturated blue tones of the Russian winter campaign",
        [_slider("Intensity", 50), _color("Cold Tint", "#b0c4de"),
         _slider("Frost", 20)],
    ))
    effects.append(_build_effect(
        "tricolore", "Tricolore", cat.NAPOLEON_THEMED.value,
        "Subtle French tricolour vignette border",
        [_slider("Intensity", 25),
         _color("Blue", "#002395"), _color("White", "#ffffff"),
         _color("Red", "#ed2939")],
    ))
    effects.append(_build_effect(
        "cavalry_dust", "Cavalry Dust", cat.NAPOLEON_THEMED.value,
        "Dust clouds kicked up by charging cavalry",
        [_slider("Density", 35), _slider("Height", 30),
         _color("Dust Color", "#c4a882")],
    ))
    effects.append(_build_effect(
        "eagle_glow", "Eagle Standard Glow", cat.NAPOLEON_THEMED.value,
        "A radiant glow surrounding the Imperial Eagle",
        [_slider("Glow Radius", 50), _slider("Intensity", 40),
         _color("Glow Color", "#ffd700")],
    ))

    return effects


# ══════════════════════════════════════════════════════════════
# Effects Configuration
# ══════════════════════════════════════════════════════════════

@dataclass
class EffectsConfig:
    """Persistent configuration for the effects overlay."""
    enabled: bool = False
    active_preset: str = "default"
    presets: Dict[str, EffectsPreset] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'active_preset': self.active_preset,
            'presets': {k: v.to_dict() for k, v in self.presets.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EffectsConfig':
        presets = {}
        for pname, pdata in data.get('presets', {}).items():
            presets[pname] = EffectsPreset.from_dict(pdata)
        return cls(
            enabled=data.get('enabled', False),
            active_preset=data.get('active_preset', 'default'),
            presets=presets,
        )


# ══════════════════════════════════════════════════════════════
# Built-in presets
# ══════════════════════════════════════════════════════════════

def _make_preset(name: str, description: str,
                 entries: Dict[str, Dict[str, Any]]) -> EffectsPreset:
    effects: Dict[str, EffectState] = {}
    for eid, vals in entries.items():
        effects[eid] = EffectState(enabled=True, values=vals)
    return EffectsPreset(name=name, description=description, effects=effects)


def get_builtin_presets() -> Dict[str, EffectsPreset]:
    """Return a dictionary of built-in presets."""
    presets: Dict[str, EffectsPreset] = {}

    presets["default"] = EffectsPreset(
        name="Default (No Effects)",
        description="All effects disabled — vanilla visuals",
    )

    presets["cinematic_war"] = _make_preset(
        "Cinematic Warfare",
        "Dramatic cinematic look with vignette, bloom & colour grading",
        {
            "vignette": {"Intensity": 55, "Radius": 50, "Softness": 80,
                         "Vignette Color": "#000000"},
            "bloom": {"Intensity": 25, "Threshold": 75, "Radius": 35,
                      "Bloom Tint": "#fffaf0"},
            "color_grading": {"Intensity": 60, "Lift": "#0a0a14",
                              "Gamma": "#807060", "Gain": "#fffbe6"},
            "letterbox": {"Bar Size": 8, "Bar Color": "#000000"},
            "film_grain": {"Intensity": 10, "Size": 30,
                           "Coloured Grain": False},
        },
    )

    presets["napoleon_glory"] = _make_preset(
        "Napoleon's Glory",
        "Imperial gold tones with battle atmosphere",
        {
            "imperial_gold": {"Intensity": 50, "Gold Tint": "#d4af37"},
            "vibrance": {"Intensity": 60, "Tint Color": "#ffffff"},
            "bloom": {"Intensity": 20, "Threshold": 80, "Radius": 30,
                      "Bloom Tint": "#ffd700"},
            "battle_smoke": {"Density": 25, "Drift Speed": 20,
                             "Smoke Color": "#8b8378"},
            "eagle_glow": {"Glow Radius": 45, "Intensity": 35,
                           "Glow Color": "#ffd700"},
        },
    )

    presets["russian_winter"] = _make_preset(
        "Russian Winter",
        "Cold desaturated look of the Eastern Front",
        {
            "winter_campaign": {"Intensity": 65, "Cold Tint": "#b0c4de",
                                "Frost": 35},
            "saturation": {"Amount": -30, "Preserve Luminance": True},
            "fog": {"Density": 40, "Start Distance": 15,
                    "Fog Color": "#d0d8e0"},
            "contrast": {"Amount": 40},
            "vignette": {"Intensity": 35, "Radius": 65, "Softness": 75,
                         "Vignette Color": "#0a0a1e"},
        },
    )

    presets["vibrant_battles"] = _make_preset(
        "Vibrant Battles",
        "Punchy saturated colours for vivid gameplay",
        {
            "vibrance": {"Intensity": 75, "Tint Color": "#ffffff"},
            "saturation": {"Amount": 25, "Preserve Luminance": True},
            "contrast": {"Amount": 55},
            "sharpen": {"Amount": 45, "Radius": 1.5},
            "bloom": {"Intensity": 15, "Threshold": 85, "Radius": 25,
                      "Bloom Tint": "#ffffff"},
        },
    )

    presets["old_painting"] = _make_preset(
        "Old Oil Painting",
        "Artistic oil-painting aesthetic with warm tones",
        {
            "oil_painting": {"Brush Size": 6, "Smoothness": 65},
            "sepia_tone": {"Intensity": 25, "Tone Color": "#704214"},
            "vignette": {"Intensity": 45, "Radius": 55, "Softness": 80,
                         "Vignette Color": "#1a0f00"},
            "film_grain": {"Intensity": 15, "Size": 50,
                           "Coloured Grain": False},
            "bloom": {"Intensity": 15, "Threshold": 80, "Radius": 30,
                      "Bloom Tint": "#ffeedd"},
        },
    )

    presets["battlefield_grit"] = _make_preset(
        "Battlefield Grit",
        "Gritty desaturated war-correspondent look",
        {
            "saturation": {"Amount": -20, "Preserve Luminance": False},
            "contrast": {"Amount": 60},
            "film_grain": {"Intensity": 25, "Size": 35,
                           "Coloured Grain": False},
            "vignette": {"Intensity": 50, "Radius": 45, "Softness": 65,
                         "Vignette Color": "#000000"},
            "battle_smoke": {"Density": 30, "Drift Speed": 25,
                             "Smoke Color": "#606060"},
            "sharpen": {"Amount": 40, "Radius": 2},
        },
    )

    return presets


# ══════════════════════════════════════════════════════════════
# Effects Overlay (main class)
# ══════════════════════════════════════════════════════════════

class EffectsOverlay:
    """
    Custom reshade-style effects overlay for Napoleon Total War.

    Provides 54 visual effects in 8 categories with sliders, colour pickers
    and toggle switches.  Supports named presets for quick switching.
    Works as a transparent always-on-top window using PyQt6 when available,
    with a console-text fallback otherwise.
    """

    def __init__(self, effects_config: Optional[EffectsConfig] = None):
        """
        Initialise the effects overlay.

        Args:
            effects_config: Optional persisted configuration; defaults created
                            if not provided.
        """
        self.effects_registry: List[EffectDefinition] = build_default_effects()
        self._effects_by_id: Dict[str, EffectDefinition] = {
            e.effect_id: e for e in self.effects_registry
        }

        # Config / presets
        if effects_config is not None:
            self.config = effects_config
        else:
            self.config = EffectsConfig()

        # Ensure built-in presets exist
        for pname, preset in get_builtin_presets().items():
            if pname not in self.config.presets:
                self.config.presets[pname] = preset

        # Live state: effect_id -> EffectState
        self._state: Dict[str, EffectState] = {}
        self._init_state_from_preset(self.config.active_preset)

        # UI references (populated by create_overlay)
        self.window: Optional[Any] = None
        self.visible: bool = False
        self._tab_widget: Optional[Any] = None

    # ── State helpers ─────────────────────────────────────────

    def _init_state_from_preset(self, preset_name: str) -> None:
        """Initialise live state from a preset (or defaults)."""
        self._state.clear()
        # Start with defaults from registry
        for edef in self.effects_registry:
            self._state[edef.effect_id] = EffectState(
                enabled=False,
                values={p.name: p.default_value for p in edef.parameters},
            )
        # Overlay with preset
        preset = self.config.presets.get(preset_name)
        if preset:
            for eid, estate in preset.effects.items():
                if eid in self._state:
                    self._state[eid].enabled = estate.enabled
                    self._state[eid].values.update(estate.values)

    # ── Public API ────────────────────────────────────────────

    def get_effect_definitions(self) -> List[EffectDefinition]:
        """Return all registered effect definitions."""
        return list(self.effects_registry)

    def get_effect(self, effect_id: str) -> Optional[EffectDefinition]:
        """Return definition for a specific effect or None."""
        return self._effects_by_id.get(effect_id)

    def get_state(self, effect_id: str) -> Optional[EffectState]:
        """Return live state for a specific effect or None."""
        return self._state.get(effect_id)

    def set_effect_enabled(self, effect_id: str, enabled: bool) -> bool:
        """Enable or disable an effect. Returns True on success."""
        state = self._state.get(effect_id)
        if state is None:
            return False
        state.enabled = enabled
        return True

    def set_effect_value(self, effect_id: str, param_name: str,
                         value: Any) -> bool:
        """Set a parameter value for an effect. Returns True on success."""
        state = self._state.get(effect_id)
        if state is None:
            return False
        edef = self._effects_by_id.get(effect_id)
        if edef is None:
            return False
        param_names = {p.name for p in edef.parameters}
        if param_name not in param_names:
            return False
        state.values[param_name] = value
        return True

    def get_active_effects(self) -> Dict[str, EffectState]:
        """Return dict of currently enabled effects."""
        return {eid: s for eid, s in self._state.items() if s.enabled}

    def get_effects_by_category(self, category: str) -> List[EffectDefinition]:
        """Return effects belonging to a specific category."""
        return [e for e in self.effects_registry if e.category == category]

    def get_categories(self) -> Dict[str, str]:
        """Return category values mapped to display names."""
        return EffectCategory.display_names()

    def get_preset_names(self) -> List[str]:
        """Return list of available preset names."""
        return list(self.config.presets.keys())

    def apply_preset(self, preset_name: str) -> bool:
        """Apply a preset, updating live state. Returns True on success."""
        if preset_name not in self.config.presets:
            return False
        self.config.active_preset = preset_name
        self._init_state_from_preset(preset_name)
        return True

    def save_current_as_preset(self, name: str,
                               description: str = "") -> bool:
        """Save the current live state as a named preset."""
        if not name:
            return False
        effects: Dict[str, EffectState] = {}
        for eid, state in self._state.items():
            if state.enabled:
                effects[eid] = EffectState(
                    enabled=True, values=dict(state.values))
        self.config.presets[name] = EffectsPreset(
            name=name, description=description, effects=effects)
        return True

    def delete_preset(self, name: str) -> bool:
        """Delete a preset. Built-in 'default' cannot be deleted."""
        if name == "default" or name not in self.config.presets:
            return False
        del self.config.presets[name]
        if self.config.active_preset == name:
            self.config.active_preset = "default"
            self._init_state_from_preset("default")
        return True

    def get_config_dict(self) -> Dict[str, Any]:
        """Export current configuration as a serialisable dictionary."""
        return self.config.to_dict()

    def get_effect_count(self) -> int:
        """Return total number of registered effects."""
        return len(self.effects_registry)

    def get_enabled_count(self) -> int:
        """Return number of currently enabled effects."""
        return sum(1 for s in self._state.values() if s.enabled)

    # ── UI creation ───────────────────────────────────────────

    def create_overlay(self) -> bool:
        """
        Create the effects overlay window.

        Returns:
            True if the overlay was created successfully, False otherwise.
        """
        if not PYQT_AVAILABLE:
            logger.warning("PyQt6 not available – effects overlay disabled")
            return False

        try:
            self.window = _EffectsOverlayWindow(self)
            return True
        except Exception as e:
            logger.error("Failed to create effects overlay: %s", e)
            return False

    def show(self) -> None:
        """Show the effects overlay."""
        if self.window:
            self.window.show()
            self.visible = True

    def hide(self) -> None:
        """Hide the effects overlay."""
        if self.window:
            self.window.hide()
            self.visible = False

    def toggle(self) -> None:
        """Toggle effects overlay visibility."""
        if self.visible:
            self.hide()
        else:
            self.show()

    def close(self) -> None:
        """Close the overlay window."""
        if self.window:
            self.window.close()
            self.window = None
        self.visible = False

    def is_visible(self) -> bool:
        """Check if the overlay is currently visible."""
        return self.visible


# ══════════════════════════════════════════════════════════════
# PyQt6 Overlay Window (only instantiated when PyQt6 is present)
# ══════════════════════════════════════════════════════════════

if PYQT_AVAILABLE:

    class _EffectsOverlayWindow(QWidget):
        """
        The actual PyQt6 window for the effects overlay.
        Transparent, frameless, always-on-top panel with tabbed categories.
        """

        def __init__(self, overlay: EffectsOverlay, parent=None):
            super().__init__(parent)
            self._overlay = overlay
            self._param_widgets: Dict[str, Dict[str, QWidget]] = {}
            self._setup_window()
            self._build_ui()

        # ── Window setup ──────────────────────────────────────

        def _setup_window(self):
            self.setWindowTitle("⚔️ Napoleon Effects")
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.Tool
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setFixedSize(380, 600)

            # Position top-left of screen (the cheat overlay is top-right)
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move(geo.x() + 10, geo.y() + 10)

        # ── Build full UI ─────────────────────────────────────

        def _build_ui(self):
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)

            container = QFrame()
            container.setObjectName("effectsContainer")
            container.setStyleSheet("""
                QFrame#effectsContainer {
                    background-color: rgba(10, 10, 18, 230);
                    border: 1px solid #d4af37;
                    border-radius: 8px;
                }
            """)
            inner = QVBoxLayout(container)
            inner.setContentsMargins(8, 8, 8, 8)
            inner.setSpacing(4)

            # Title row
            title = QLabel("⚔️ Napoleon Visual Effects")
            title.setStyleSheet(
                "color: #d4af37; font-size: 15px; font-weight: bold;"
            )
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner.addWidget(title)

            # Preset selector row
            preset_row = QHBoxLayout()
            preset_label = QLabel("Preset:")
            preset_label.setStyleSheet("color: #cccccc; font-size: 11px;")
            preset_row.addWidget(preset_label)

            self._preset_combo = QComboBox()
            self._preset_combo.setStyleSheet(self._combo_style())
            self._refresh_preset_combo()
            self._preset_combo.currentTextChanged.connect(self._on_preset_changed)
            preset_row.addWidget(self._preset_combo, 1)

            save_btn = QPushButton("💾")
            save_btn.setToolTip("Save current settings as new preset")
            save_btn.setFixedSize(28, 28)
            save_btn.setStyleSheet(self._button_style())
            save_btn.clicked.connect(self._on_save_preset)
            preset_row.addWidget(save_btn)

            inner.addLayout(preset_row)

            # Tabs for categories
            self._tab_widget = QTabWidget()
            self._tab_widget.setStyleSheet(self._tab_style())
            self._build_category_tabs()
            inner.addWidget(self._tab_widget, 1)

            # Status bar
            self._status_label = QLabel()
            self._status_label.setStyleSheet(
                "color: #888888; font-size: 10px; padding: 2px;"
            )
            self._update_status()
            inner.addWidget(self._status_label)

            root.addWidget(container)

        # ── Category tabs ─────────────────────────────────────

        def _build_category_tabs(self):
            cat_names = EffectCategory.display_names()
            for cat in EffectCategory:
                effects = self._overlay.get_effects_by_category(cat.value)
                if not effects:
                    continue

                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setStyleSheet(
                    "QScrollArea { border: none; background: transparent; }"
                )

                content = QWidget()
                layout = QVBoxLayout(content)
                layout.setContentsMargins(4, 4, 4, 4)
                layout.setSpacing(3)

                for edef in effects:
                    group = self._create_effect_group(edef)
                    layout.addWidget(group)

                layout.addStretch()
                scroll.setWidget(content)
                self._tab_widget.addTab(scroll, cat_names[cat.value])

        def _create_effect_group(self, edef: EffectDefinition) -> QGroupBox:
            state = self._overlay.get_state(edef.effect_id)
            group = QGroupBox()
            group.setTitle(edef.name)
            group.setCheckable(True)
            group.setChecked(state.enabled if state else False)
            group.setToolTip(edef.description)
            group.setStyleSheet(self._group_style())
            group.toggled.connect(
                lambda checked, eid=edef.effect_id: self._on_effect_toggled(eid, checked)
            )

            glayout = QGridLayout(group)
            glayout.setContentsMargins(6, 4, 6, 4)
            glayout.setSpacing(3)

            self._param_widgets[edef.effect_id] = {}

            for row, param in enumerate(edef.parameters):
                label = QLabel(param.name)
                label.setStyleSheet("color: #cccccc; font-size: 10px;")
                glayout.addWidget(label, row, 0)

                if param.param_type == "slider":
                    widget = self._create_slider(edef.effect_id, param, state)
                    glayout.addWidget(widget, row, 1)
                elif param.param_type == "color":
                    widget = self._create_color_button(edef.effect_id, param, state)
                    glayout.addWidget(widget, row, 1)
                elif param.param_type == "toggle":
                    widget = self._create_toggle(edef.effect_id, param, state)
                    glayout.addWidget(widget, row, 1)

            return group

        # ── Slider widget ─────────────────────────────────────

        def _create_slider(self, effect_id: str, param: EffectParameter,
                           state: Optional[EffectState]) -> QWidget:
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)

            slider = QSlider(Qt.Orientation.Horizontal)
            steps = int((param.max_value - param.min_value) / param.step) if param.step else 100
            slider.setMinimum(0)
            slider.setMaximum(steps)
            slider.setStyleSheet(self._slider_style())

            cur = state.values.get(param.name, param.default_value) if state else param.default_value
            pos = int((cur - param.min_value) / param.step) if param.step else 0
            slider.setValue(pos)

            value_label = QLabel(f"{cur}{param.suffix}")
            value_label.setFixedWidth(50)
            value_label.setStyleSheet("color: #d4af37; font-size: 10px;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            def on_change(v, eid=effect_id, p=param, lbl=value_label):
                real_val = p.min_value + v * p.step
                lbl.setText(f"{real_val:.4g}{p.suffix}")
                self._overlay.set_effect_value(eid, p.name, real_val)

            slider.valueChanged.connect(on_change)

            h.addWidget(slider, 1)
            h.addWidget(value_label)
            self._param_widgets[effect_id][param.name] = slider
            return container

        # ── Colour button widget ──────────────────────────────

        def _create_color_button(self, effect_id: str, param: EffectParameter,
                                 state: Optional[EffectState]) -> QPushButton:
            cur = state.values.get(param.name, param.default_value) if state else param.default_value
            btn = QPushButton()
            btn.setFixedSize(60, 22)
            btn.setStyleSheet(
                f"background-color: {cur}; border: 1px solid #d4af37; "
                f"border-radius: 3px;"
            )
            btn.setToolTip(f"Click to choose {param.name}")

            def on_click(_=False, eid=effect_id, p=param, b=btn):
                colour = QColorDialog.getColor(
                    QColor(b.styleSheet().split("background-color:")[1].split(";")[0].strip()),
                    self,
                    f"Choose {p.name}",
                )
                if colour.isValid():
                    hex_col = colour.name()
                    b.setStyleSheet(
                        f"background-color: {hex_col}; border: 1px solid #d4af37; "
                        f"border-radius: 3px;"
                    )
                    self._overlay.set_effect_value(eid, p.name, hex_col)

            btn.clicked.connect(on_click)
            self._param_widgets[effect_id][param.name] = btn
            return btn

        # ── Toggle widget ─────────────────────────────────────

        def _create_toggle(self, effect_id: str, param: EffectParameter,
                           state: Optional[EffectState]) -> QCheckBox:
            cur = state.values.get(param.name, param.default_value) if state else param.default_value
            cb = QCheckBox()
            cb.setChecked(bool(cur))
            cb.setStyleSheet("QCheckBox { color: #cccccc; }")

            def on_toggle(checked, eid=effect_id, p=param):
                self._overlay.set_effect_value(eid, p.name, checked)

            cb.toggled.connect(on_toggle)
            self._param_widgets[effect_id][param.name] = cb
            return cb

        # ── Preset helpers ────────────────────────────────────

        def _refresh_preset_combo(self):
            self._preset_combo.blockSignals(True)
            self._preset_combo.clear()
            for pname, preset in self._overlay.config.presets.items():
                display = preset.name if preset.name else pname
                self._preset_combo.addItem(display, pname)
            # Select the active preset
            idx = self._preset_combo.findData(self._overlay.config.active_preset)
            if idx >= 0:
                self._preset_combo.setCurrentIndex(idx)
            self._preset_combo.blockSignals(False)

        def _on_preset_changed(self, text: str):
            idx = self._preset_combo.currentIndex()
            key = self._preset_combo.itemData(idx)
            if key and self._overlay.apply_preset(key):
                self._rebuild_tabs()
                self._update_status()

        def _on_save_preset(self):
            from PyQt6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(
                self, "Save Preset", "Preset name:")
            if ok and name.strip():
                self._overlay.save_current_as_preset(name.strip())
                self._refresh_preset_combo()

        def _rebuild_tabs(self):
            self._tab_widget.clear()
            self._param_widgets.clear()
            self._build_category_tabs()

        def _on_effect_toggled(self, effect_id: str, checked: bool):
            self._overlay.set_effect_enabled(effect_id, checked)
            self._update_status()

        def _update_status(self):
            total = self._overlay.get_effect_count()
            active = self._overlay.get_enabled_count()
            self._status_label.setText(
                f"Effects: {active}/{total} active  |  "
                f"Preset: {self._overlay.config.active_preset}"
            )

        # ── Stylesheet helpers ────────────────────────────────

        @staticmethod
        def _combo_style() -> str:
            return """
                QComboBox {
                    background-color: rgba(30, 30, 40, 200);
                    color: #d4af37;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 2px 6px;
                    font-size: 11px;
                }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView {
                    background-color: #1a1a28;
                    color: #d4af37;
                    selection-background-color: #333;
                }
            """

        @staticmethod
        def _button_style() -> str:
            return """
                QPushButton {
                    background-color: rgba(30, 30, 40, 200);
                    color: #d4af37;
                    border: 1px solid #555;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(60, 60, 80, 200);
                }
            """

        @staticmethod
        def _tab_style() -> str:
            return """
                QTabWidget::pane {
                    border: 1px solid #333;
                    background: transparent;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background: rgba(20, 20, 30, 200);
                    color: #aaaaaa;
                    padding: 4px 8px;
                    margin: 1px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QTabBar::tab:selected {
                    background: rgba(50, 50, 70, 220);
                    color: #d4af37;
                }
            """

        @staticmethod
        def _group_style() -> str:
            return """
                QGroupBox {
                    color: #d4af37;
                    border: 1px solid #444;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 12px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 4px;
                }
                QGroupBox::indicator {
                    width: 14px; height: 14px;
                }
                QGroupBox::indicator:checked {
                    background-color: #00cc44;
                    border: 1px solid #009933;
                    border-radius: 2px;
                }
                QGroupBox::indicator:unchecked {
                    background-color: #333;
                    border: 1px solid #555;
                    border-radius: 2px;
                }
            """

        @staticmethod
        def _slider_style() -> str:
            return """
                QSlider::groove:horizontal {
                    height: 4px;
                    background: #333;
                    border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    background: #d4af37;
                    width: 12px;
                    height: 12px;
                    margin: -4px 0;
                    border-radius: 6px;
                }
                QSlider::sub-page:horizontal {
                    background: #8b7520;
                    border-radius: 2px;
                }
            """


# ══════════════════════════════════════════════════════════════
# Console fallback
# ══════════════════════════════════════════════════════════════

class SimpleEffectsOverlay:
    """Console fallback when PyQt6 is unavailable."""

    def __init__(self, effects_config: Optional[EffectsConfig] = None):
        self._overlay = EffectsOverlay(effects_config)

    def show(self) -> None:
        active = self._overlay.get_active_effects()
        if active:
            print(f"\n⚔️ Active Effects ({len(active)}):")
            for eid, state in active.items():
                edef = self._overlay.get_effect(eid)
                name = edef.name if edef else eid
                print(f"  ✓ {name}")
            print()
        else:
            print("\n⚔️ No effects active\n")

    def hide(self) -> None:
        pass

    def toggle(self) -> None:
        self.show()

    def close(self) -> None:
        pass
