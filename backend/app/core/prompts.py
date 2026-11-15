"""
CreateX AI – Gemini Prompt Templates
All prompts live here so they can be iterated without touching business logic.
"""

CAMPAIGN_SYSTEM_PROMPT = """You are a world-class creative director and brand strategist.
Your task is to analyze a creative idea and generate a comprehensive campaign context.
Always respond with valid JSON matching the exact schema provided.
Be specific, creative, and ensure all elements are cohesive and consistent."""

CAMPAIGN_PROMPT_TEMPLATE = """Analyze this creative idea and generate a complete campaign context.

Creative Idea: {idea}
Industry: {industry}
Target Audience: {target_audience}
Campaign Tone: {tone}
Preferred Platforms: {platforms}
Visual Style: {visual_style}

Generate a JSON response with this exact structure:
{{
  "campaign_name": "Creative campaign name",
  "tagline": "Memorable tagline under 10 words",
  "description": "2-3 sentence campaign description",
  "target_audience": "Refined target audience description",
  "brand_colors": {{
    "primary": "#hexcode",
    "secondary": "#hexcode",
    "accent": "#hexcode",
    "background": "#hexcode"
  }},
  "creative_concepts": ["concept 1", "concept 2", "concept 3"],
  "visual_direction": "Detailed visual direction paragraph describing style, mood, imagery",
  "writing_tone": "Description of the writing tone and voice",
  "poster_generation_prompt": "Detailed prompt for AI image generation of the campaign poster",
  "key_messages": ["message 1", "message 2", "message 3"],
  "campaign_themes": ["theme 1", "theme 2"]
}}"""

STORYBOARD_SYSTEM_PROMPT = """You are an expert video director and storyboard artist.
Create detailed, cinematic scene-by-scene video storyboards.
Always respond with valid JSON matching the exact schema provided.
Make each scene vivid, purposeful, and narratively compelling."""

STORYBOARD_PROMPT_TEMPLATE = """Create a video storyboard for this campaign.

Campaign Name: {campaign_name}
Tagline: {tagline}
Campaign Description: {description}
Visual Direction: {visual_direction}
Target Audience: {target_audience}
Brand Colors: {brand_colors}
Video Duration: {video_duration} seconds
Number of Scenes: {num_scenes}
Platform: {platform}
Creative Tone: {tone}

Generate a JSON response with this exact structure:
{{
  "video_title": "Title for the video",
  "total_duration": {video_duration},
  "platform": "{platform}",
  "scenes": [
    {{
      "scene_number": 1,
      "duration_seconds": 5,
      "visual_description": "Detailed description of what appears on screen",
      "camera_direction": "Camera angle, movement, and shot type",
      "narration": "Voice-over or spoken dialogue",
      "on_screen_text": "Any text overlays or captions",
      "transition": "Transition to next scene",
      "mood": "Emotional tone of this scene"
    }}
  ]
}}
Generate exactly {num_scenes} scenes that add up to approximately {video_duration} seconds total."""

SOCIAL_SYSTEM_PROMPT = """You are a creative social media strategist and copywriter.
Generate platform-optimized social media content that is engaging, authentic, and drives action.
Always respond with valid JSON matching the exact schema provided.
Maintain brand voice and campaign identity throughout."""

SOCIAL_PROMPT_TEMPLATE = """Generate social media content for this campaign.

Campaign Name: {campaign_name}
Tagline: {tagline}
Campaign Description: {description}
Target Audience: {target_audience}
Writing Tone: {writing_tone}
Key Messages: {key_messages}
Platforms: {platforms}

Generate a JSON response with this exact structure:
{{
  "instagram": {{
    "captions": [
      "Caption variation 1 (include emojis, compelling hook)",
      "Caption variation 2 (different angle)",
      "Caption variation 3 (story-driven)"
    ],
    "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5",
                 "hashtag6", "hashtag7", "hashtag8", "hashtag9", "hashtag10"],
    "cta": "Call to action text",
    "story_text": "Short text for Instagram Stories"
  }},
  "youtube": {{
    "title": "Compelling YouTube video title",
    "description": "Full YouTube video description (2-3 paragraphs)",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "thumbnail_text": "Text overlay for thumbnail",
    "cta": "Call to action for YouTube"
  }},
  "headlines": [
    "Promotional headline 1",
    "Promotional headline 2",
    "Promotional headline 3"
  ],
  "ad_copy": "Short advertising copy (2-3 sentences)"
}}"""
