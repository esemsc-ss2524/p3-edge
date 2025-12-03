# P3-Edge Character Animations

This directory contains character animations for the P3-Edge autonomous grocery assistant.

## Required Files

### p3_idle.gif
The idle animation showing P3 standing/waiting. This plays continuously when P3 is not actively processing.

**Specifications:**
- Format: Animated GIF
- Recommended size: 200x200 pixels or similar square aspect
- Loop: Infinite
- Style: Friendly, approachable character

### p3_wave.gif
The waving animation showing P3 greeting or acknowledging the user. This plays when:
- User sends a message
- P3 starts thinking/processing
- P3 wants to get attention

**Specifications:**
- Format: Animated GIF
- Recommended size: 200x200 pixels (same as idle)
- Duration: ~2 seconds
- Loop: Once (returns to idle after playing)
- Style: Enthusiastic, welcoming gesture

## Usage

The animations are loaded automatically by the P3Dashboard UI component. If the GIF files are not found, the UI will show a robot emoji (🤖) as a placeholder.

## Creating Your Own Animations

You can create custom animations using:
- Animation software (Adobe Animate, After Effects, etc.)
- Sprite sheet tools
- AI image generation tools
- Hand-drawn frames compiled into GIF

Make sure to maintain consistency in:
- Character design between idle and wave
- Size and positioning
- Color scheme (matches UI theme)
- Frame rate (smooth but not too fast)

## Current Status

⚠️ **Placeholder Mode**: The character animations are not yet provided. The UI will display a robot emoji until the GIF files are added to this directory.

To add your character:
1. Create or obtain `p3_idle.gif` and `p3_wave.gif`
2. Place them in this `assets/` directory
3. Restart the application
4. P3 will now display with your character!
