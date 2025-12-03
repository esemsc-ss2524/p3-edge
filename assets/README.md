# P3-Edge Character Animations

This directory contains character animations for the P3-Edge autonomous grocery assistant.

## Required Files

### p3_idle.webp
The idle animation showing P3 standing/waiting. This plays continuously when P3 is not actively processing.

**Specifications:**
- Format: Animated GIF
- Recommended size: 400x400 pixels (fills 80% of left panel)
- Loop: Infinite
- Style: Friendly, approachable character
- **When it plays**: Default state, after wave/thinking animations complete

### p3_wave.webp
The waving animation showing P3 greeting or acknowledging the user.

**Specifications:**
- Format: Animated GIF
- Recommended size: 400x400 pixels (same as idle)
- Duration: ~2 seconds
- Loop: Once (returns to idle after playing)
- Style: Enthusiastic, welcoming gesture
- **When it plays**: When you click on the character

### p3_thinking.webp
The thinking animation showing P3 processing your request.

**Specifications:**
- Format: Animated GIF
- Recommended size: 400x400 pixels (same as idle)
- Loop: Continuous (while thinking)
- Style: Contemplative, focused expression
- **When it plays**: When LLM is processing your message

## Usage

The animations are loaded automatically by the P3Dashboard UI component. If the GIF files are not found, the UI will show a robot emoji (🤖) as a placeholder.

## Animation Behavior

- **Idle** → Plays continuously when P3 is waiting
- **Click character** → Plays wave animation (2s) → Returns to idle
- **Send message** → Plays thinking animation → Returns to idle when done
- **No GIFs?** → Shows 🤖 emoji placeholder (fully functional)

## Creating Your Own Animations

You can create custom animations using:
- Animation software (Adobe Animate, After Effects, etc.)
- Sprite sheet tools
- AI image generation tools
- Hand-drawn frames compiled into GIF

Make sure to maintain consistency in:
- Character design between idle, wave, and thinking
- Size and positioning (400x400px recommended)
- Color scheme (matches UI theme)
- Frame rate (smooth but not too fast)

## Current Status

⚠️ **Placeholder Mode**: The character animations are not yet provided. The UI will display a robot emoji until the GIF files are added to this directory.

To add your character:
1. Create or obtain `p3_idle.webp`, `p3_wave.webp`, and `p3_thinking.webp`
2. Place them in this `assets/` directory
3. Restart the application
4. P3 will now display with your character!

## Size Guidelines

The character area takes up 80% of the vertical space in the left panel, so animations should be:
- Large enough to be visible (400x400px+)
- Square aspect ratio preferred
- Not too detailed (will be scaled to fit)
- Optimized file size (keep under 2MB for smooth loading)
