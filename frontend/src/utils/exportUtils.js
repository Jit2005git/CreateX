/**
 * Export utilities for CreateX AI Campaign Dossier
 * Generates formatted Markdown dossiers and structured JSON exports.
 */

export function generateMarkdownDossier(campaign, assets = {}, metadata = {}) {
  if (!campaign) return ''

  const dateStr = metadata.created_at
    ? new Date(metadata.created_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    : new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })

  const updatedStr = metadata.updated_at
    ? new Date(metadata.updated_at).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Just now'

  const poster = assets.poster || null
  const storyboard = assets.storyboard || null
  const social = assets.social || null

  let md = `# ${campaign.campaign_name || 'Untitled Campaign'}
> "${campaign.tagline || 'One Idea. Multiple Creative Possibilities.'}"

**Created with CreateX AI**  
**Date:** ${dateStr} (Last updated: ${updatedStr})  
**Industry:** ${campaign.industry || 'General'} | **Tone:** ${campaign.tone || campaign.writing_tone || 'Professional'} | **Visual Style:** ${campaign.visual_style || 'Modern'}

---

## 1. Executive Summary & Brand Strategy

### Original Concept
${campaign.original_idea || campaign.description || 'N/A'}

### Campaign Description
${campaign.description || 'N/A'}

### Target Audience
${campaign.target_audience || 'General Consumer'}

### Brand Color Palette
| Role | Hex Code | Swatch |
|------|----------|--------|
| Primary | \`${campaign.brand_colors?.primary || '#7C3AED'}\` | █ |
| Secondary | \`${campaign.brand_colors?.secondary || '#06B6D4'}\` | █ |
| Accent | \`${campaign.brand_colors?.accent || '#F59E0B'}\` | █ |
| Background | \`${campaign.brand_colors?.background || '#0F0F1A'}\` | █ |

### Creative Concepts
${
  campaign.creative_concepts?.length > 0
    ? campaign.creative_concepts.map((c, i) => `${i + 1}. **${c}**`).join('\n')
    : '_No creative concepts defined._'
}

### Visual Direction
${campaign.visual_direction || '_Visual direction pending._'}

### Key Brand Messages
${
  campaign.key_messages?.length > 0
    ? campaign.key_messages.map(m => `- ${m}`).join('\n')
    : '_No key messages defined._'
}

---

## 2. Promotional Poster Asset
`

  if (poster?.image_url) {
    md += `
- **Status:** Generated
- **Image URL:** [${poster.image_url}](${poster.image_url})
- **Storage Reference:** \`${poster.storage_path || 'local/storage'}\`
- **Prompt Used:**
> ${poster.prompt_used || 'Standard campaign prompt'}
`
  } else {
    md += `
_Poster has not been generated yet. Open the Poster Studio in CreateX AI to generate this asset._
`
  }

  md += `
---

## 3. Video Storyboard
`

  if (storyboard?.scenes?.length > 0) {
    md += `
- **Video Title:** ${storyboard.video_title || campaign.campaign_name}
- **Total Duration:** ${storyboard.total_duration || 30} seconds
- **Target Platform:** ${storyboard.platform || 'General'}
- **Scene Count:** ${storyboard.scenes.length} scenes

### Scene-by-Scene Breakdown

| Scene | Duration | Visual Description | Camera & Shot | Audio & Narration | On-Screen Text |
|:-----:|:--------:|--------------------|---------------|-------------------|----------------|
`
    storyboard.scenes.forEach(s => {
      const visual = (s.visual_description || '').replace(/\|/g, '\\|').replace(/\n/g, ' ')
      const camera = (s.camera_direction || '').replace(/\|/g, '\\|').replace(/\n/g, ' ')
      const narration = (s.narration || '').replace(/\|/g, '\\|').replace(/\n/g, ' ')
      const text = (s.on_screen_text || '-').replace(/\|/g, '\\|').replace(/\n/g, ' ')
      md += `| ${s.scene_number} | ${s.duration_seconds}s | ${visual} | ${camera} | ${narration} | ${text} |\n`
    })
  } else {
    md += `
_Storyboard has not been generated yet. Open the Storyboard Studio in CreateX AI to generate this asset._
`
  }

  md += `
---

## 4. Social Media Campaign Strategy
`

  if (social) {
    if (social.headlines?.length > 0) {
      md += `
### Promotional Headlines
${social.headlines.map(h => `- **${h}**`).join('\n')}
`
    }

    if (social.ad_copy) {
      md += `
### Core Advertising Copy
> ${social.ad_copy}
`
    }

    if (social.instagram) {
      md += `
### Instagram Marketing Package
**Caption Variations:**
${
  social.instagram.captions?.length > 0
    ? social.instagram.captions.map((cap, i) => `${i + 1}. ${cap}`).join('\n\n')
    : '_None_'
}

**Hashtags:**  
${
  social.instagram.hashtags?.length > 0
    ? social.instagram.hashtags.map(h => (h.startsWith('#') ? h : `#${h}`)).join(' ')
    : '_None_'
}

**Call to Action:**  
*${social.instagram.cta || 'Tap the link in bio to learn more.'}*

${social.instagram.story_text ? `**Stories Copy:**\n> ${social.instagram.story_text}\n` : ''}
`
    }

    if (social.youtube) {
      md += `
### YouTube Video Package
- **Title:** ${social.youtube.title || 'Official Launch'}
- **Call to Action:** ${social.youtube.cta || 'Subscribe for more.'}
${social.youtube.thumbnail_text ? `- **Thumbnail Overlay:** \`${social.youtube.thumbnail_text}\`` : ''}

**Description:**
\`\`\`text
${social.youtube.description || ''}
\`\`\`

**Search Tags:**  
${
  social.youtube.tags?.length > 0
    ? social.youtube.tags.map(t => `\`${t}\``).join(', ')
    : '_None_'
}
`
    }
  } else {
    md += `
_Social media package has not been generated yet. Open the Social Studio in CreateX AI to generate this asset._
`
  }

  md += `
---
*Produced by CreateX AI — One Idea. Multiple Creative Possibilities.*
`

  return md
}

export function generateCampaignJson(campaign, assets = {}, metadata = {}) {
  const exportPayload = {
    schema_version: '1.0',
    export_generator: 'CreateX AI Platform',
    exported_at: new Date().toISOString(),
    metadata: {
      created_at: metadata.created_at || new Date().toISOString(),
      updated_at: metadata.updated_at || new Date().toISOString(),
      project_id: metadata.project_id || 'local',
    },
    campaign: {
      name: campaign.campaign_name,
      tagline: campaign.tagline,
      description: campaign.description,
      original_idea: campaign.original_idea,
      industry: campaign.industry,
      target_audience: campaign.target_audience,
      tone: campaign.tone || campaign.writing_tone,
      visual_style: campaign.visual_style,
      visual_direction: campaign.visual_direction,
      brand_colors: campaign.brand_colors,
      creative_concepts: campaign.creative_concepts || [],
      key_messages: campaign.key_messages || [],
      campaign_themes: campaign.campaign_themes || [],
      poster_generation_prompt: campaign.poster_generation_prompt,
    },
    assets: {
      poster: assets.poster
        ? {
            image_url: assets.poster.image_url,
            storage_path: assets.poster.storage_path,
            prompt_used: assets.poster.prompt_used,
            generated_at: assets.poster.generated_at || metadata.updated_at,
          }
        : null,
      storyboard: assets.storyboard || null,
      social: assets.social || null,
    },
  }

  return JSON.stringify(exportPayload, null, 2)
}

export function downloadBlob(content, filename, mimeType = 'text/plain') {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
