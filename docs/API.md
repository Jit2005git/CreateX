# CreateX AI – API Contract

Base URL: `http://localhost:8000`  
All requests: `Content-Type: application/json`  
All responses: JSON

---

## Health

### `GET /`
```json
{ "message": "CreateX AI API is running", "version": "1.0.0" }
```

### `GET /api/health`
```json
{
  "status": "ok",
  "environment": "development",
  "gemini_configured": true,
  "supabase_configured": true
}
```

---

## Campaign

### `POST /api/campaign/generate`

**Request:**
```json
{
  "idea": "A sustainable sneaker brand for Gen Z",
  "industry": "Fashion & Apparel",
  "target_audience": "Gen Z urban consumers aged 18-24",
  "tone": "bold",
  "platforms": ["instagram", "youtube"],
  "visual_style": "modern"
}
```

**Response `200`:**
```json
{
  "success": true,
  "campaign": {
    "campaign_name": "StepForward",
    "tagline": "Walk the Change.",
    "description": "...",
    "target_audience": "...",
    "brand_colors": {
      "primary": "#2D6A4F",
      "secondary": "#52B788",
      "accent": "#D8F3DC",
      "background": "#081C15"
    },
    "creative_concepts": ["...", "..."],
    "visual_direction": "...",
    "writing_tone": "...",
    "poster_generation_prompt": "...",
    "key_messages": ["...", "..."],
    "campaign_themes": ["...", "..."]
  }
}
```

**Error `422`:** Validation error (idea too short, missing field)  
**Error `503`:** Gemini API key not configured  
**Error `500`:** Gemini API call failed  

---

## Visual

### `POST /api/visual/generate`

**Request:**
```json
{
  "campaign": { /* full CampaignContext object */ },
  "style_override": "More dramatic lighting"
}
```

**Response `200`:**
```json
{
  "success": true,
  "image_url": "https://your-project.supabase.co/storage/v1/object/public/createx-posters/posters/poster_abc123.png",
  "storage_path": "posters/poster_abc123.png",
  "prompt_used": "Create a stunning promotional poster..."
}
```

**Error `422`:** Campaign context invalid  
**Error `503`:** Gemini or Supabase not configured  
**Error `500`:** Image generation or upload failed  

---

## Storyboard

### `POST /api/storyboard/generate`

**Request:**
```json
{
  "campaign": { /* full CampaignContext object */ },
  "video_duration": 30,
  "num_scenes": 5,
  "platform": "instagram"
}
```

**Response `200`:**
```json
{
  "success": true,
  "storyboard": {
    "video_title": "StepForward – Walk the Change",
    "total_duration": 30,
    "platform": "instagram",
    "scenes": [
      {
        "scene_number": 1,
        "duration_seconds": 6,
        "visual_description": "...",
        "camera_direction": "Wide establishing shot...",
        "narration": "...",
        "on_screen_text": "Walk the Change.",
        "transition": "Fade to black",
        "mood": "Inspirational"
      }
    ]
  }
}
```

---

## Social

### `POST /api/social/generate`

**Request:**
```json
{
  "campaign": { /* full CampaignContext object */ },
  "platforms": ["instagram", "youtube"]
}
```

**Response `200`:**
```json
{
  "success": true,
  "social": {
    "instagram": {
      "captions": ["Caption 1...", "Caption 2...", "Caption 3..."],
      "hashtags": ["sustainability", "sneakers", "genz"],
      "cta": "Shop now — link in bio",
      "story_text": "Walk the Change 🌱"
    },
    "youtube": {
      "title": "Walk the Change – StepForward Official",
      "description": "...",
      "tags": ["sustainable fashion", "sneakers"],
      "thumbnail_text": "WALK THE CHANGE",
      "cta": "Subscribe for more sustainable style"
    },
    "headlines": ["Step Into Sustainability", "Your Walk, Your Impact"],
    "ad_copy": "..."
  }
}
```

---

## Projects

### `POST /api/projects/save`

**Request:**
```json
{
  "session_id": "sess_abc123",
  "title": "StepForward",
  "original_idea": "A sustainable sneaker brand...",
  "industry": "Fashion & Apparel",
  "target_audience": "Gen Z urban consumers",
  "tone": "bold",
  "platforms": ["instagram"],
  "visual_style": "modern",
  "campaign_data": { /* full CampaignContext */ }
}
```

**Response `200`:**
```json
{ "success": true, "project_id": "uuid-here", "message": "Project saved successfully" }
```

---

### `GET /api/projects?session_id=sess_abc123&limit=20`

**Response `200`:**
```json
{
  "success": true,
  "projects": [ { /* ProjectResponse */ } ],
  "total": 3
}
```

---

### `GET /api/projects/{id}`

**Response `200`:** Full `ProjectResponse` with `assets` array  
**Error `404`:** Project not found

---

### `DELETE /api/projects/{id}`

**Response `200`:**
```json
{ "success": true, "message": "Project deleted successfully." }
```

---

## Error Response Format

All errors follow this shape:
```json
{
  "detail": "Human-readable error message"
}
```
