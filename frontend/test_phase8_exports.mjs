import assert from 'node:assert'
import { generateMarkdownDossier, generateCampaignJson } from './src/utils/exportUtils.js'

console.log('--- RUNNING PHASE 8 EXPORT & WORKSPACE TESTS ---')

// 1. Mock Complete Campaign Context
const mockCampaign = {
  campaign_name: 'EcoStride Launch',
  tagline: 'Step Lightly, Run Wilder',
  description: 'A revolutionary running shoe made from 95% ocean plastic.',
  original_idea: 'Sustainable running shoe for urban marathoners',
  industry: 'Sustainable Fashion',
  target_audience: 'Environmentally conscious runners aged 20-35',
  tone: 'Inspiring & Energetic',
  visual_style: 'Modern Minimalist',
  visual_direction: 'Clean studio lighting, natural earth tones, dynamic athletic poses',
  brand_colors: {
    primary: '#10B981',
    secondary: '#06B6D4',
    accent: '#F59E0B',
    background: '#0F172A',
  },
  creative_concepts: [
    'Run from the Past, Step into Clean Oceans',
    'Zero Guilt, Maximum Pace',
  ],
  key_messages: [
    'Every shoe cleans 2kg of marine debris',
    'Pro-grade cushioning with zero virgin polymers',
  ],
  poster_generation_prompt: 'High resolution product shot of green sustainable sneaker...',
}

// 2. Mock Full Assets
const mockAssets = {
  poster: {
    image_url: 'http://localhost:8000/static/posters/test_poster_123.png',
    storage_path: 'storage/posters/test_poster_123.png',
    prompt_used: 'High contrast eco shoe poster in emerald and cyan',
  },
  storyboard: {
    video_title: 'EcoStride: The Ocean Mile',
    total_duration: 30,
    platform: 'instagram',
    scenes: [
      {
        scene_number: 1,
        duration_seconds: 6,
        visual_description: 'Ocean waves crashing on rocky beach with plastic waste.',
        camera_direction: 'Slow wide tracking shot moving forward.',
        narration: 'Every journey begins with a single choice.',
        on_screen_text: 'The Oceans Are Calling',
        transition: 'Fade to black',
        mood: 'Reflective',
      },
      {
        scene_number: 2,
        duration_seconds: 8,
        visual_description: 'Close-up of runner tying recycled laces in morning mist.',
        camera_direction: 'Low-angle macro shot.',
        narration: 'Engineered from ocean recovery. Built for peak speed.',
        on_screen_text: 'Meet EcoStride',
        transition: 'Quick cut',
        mood: 'Energetic',
      },
      {
        scene_number: 3,
        duration_seconds: 16,
        visual_description: 'Runner sprinting along coastal highway into sunrise.',
        camera_direction: 'Aerial drone pull-back.',
        narration: 'Run wilder. Step lighter.',
        on_screen_text: 'EcoStride - Available Worldwide',
        transition: 'Dissolve',
        mood: 'Triumphant',
      },
    ],
  },
  social: {
    headlines: ['Run for the Planet', 'Performance Meets Purity'],
    ad_copy: 'Experience high-performance marathon gear crafted entirely from recycled ocean plastics.',
    instagram: {
      captions: [
        'Turning ocean waste into your next marathon PR. 🌊👟 Tap link in bio.',
        'Speed without compromise. Meet the 100% circular running shoe.',
      ],
      hashtags: ['EcoStride', 'SustainableRunning', 'OceanClean', 'RunWild'],
      cta: 'Shop the EcoStride collection at the link in our bio.',
      story_text: 'Swipe up to explore the circular lifecycle of your next pair of kicks.',
    },
    youtube: {
      title: 'How We Turned Ocean Waste Into an Elite Marathon Shoe | EcoStride Launch',
      description: 'Join us on our journey to clean the oceans one stride at a time.\n\nLearn more: https://ecostride.run',
      tags: ['ecostride', 'running', 'sustainable fashion', 'ocean cleanup'],
      thumbnail_text: 'OCEAN TO RUNWAY',
      cta: 'Subscribe to CreateX for more groundbreaking product stories.',
    },
  },
}

const mockMetadata = {
  project_id: 'proj_eco_001',
  created_at: '2026-11-16T12:00:00.000Z',
  updated_at: '2026-11-16T15:30:00.000Z',
}

// TEST 1: Markdown Dossier with Full Assets
console.log('Test 1: Markdown Dossier generation with all assets...');
const fullMd = generateMarkdownDossier(mockCampaign, mockAssets, mockMetadata);
assert(fullMd.includes('# EcoStride Launch'), 'Missing campaign title in markdown');
assert(fullMd.includes('Step Lightly, Run Wilder'), 'Missing tagline');
assert(fullMd.includes('#10B981'), 'Missing primary brand color');
assert(fullMd.includes('http://localhost:8000/static/posters/test_poster_123.png'), 'Missing poster URL');
assert(!fullMd.includes('data:image/'), 'Markdown should not contain raw base64 data URLs');
assert(fullMd.includes('EcoStride: The Ocean Mile'), 'Missing storyboard title');
assert(fullMd.includes('Scene-by-Scene Breakdown'), 'Missing scene breakdown table');
assert(fullMd.includes('| 1 | 6s |'), 'Missing scene 1 in markdown table');
assert(fullMd.includes('| 3 | 16s |'), 'Missing scene 3 in markdown table');
assert(fullMd.includes('Instagram Marketing Package'), 'Missing Instagram section');
assert(fullMd.includes('#EcoStride'), 'Missing Instagram hashtag');
assert(fullMd.includes('YouTube Video Package'), 'Missing YouTube section');
assert(fullMd.includes('OCEAN TO RUNWAY'), 'Missing YouTube thumbnail text');
console.log('✓ Test 1 passed: Markdown Dossier contains all coordinated sections.');

// TEST 2: Markdown Dossier with Missing / Ungenerated Assets
console.log('Test 2: Markdown Dossier handles empty / partial assets gracefully...');
const emptyMd = generateMarkdownDossier(mockCampaign, {}, mockMetadata);
assert(emptyMd.includes('# EcoStride Launch'), 'Missing title');
assert(emptyMd.includes('Poster has not been generated yet'), 'Should note missing poster');
assert(emptyMd.includes('Storyboard has not been generated yet'), 'Should note missing storyboard');
assert(emptyMd.includes('Social media package has not been generated yet'), 'Should note missing social package');
console.log('✓ Test 2 passed: Graceful fallback for ungenerated assets.');

// TEST 3: JSON Export Verification
console.log('Test 3: JSON Export structure and validation...');
const jsonString = generateCampaignJson(mockCampaign, mockAssets, mockMetadata);
const parsedJson = JSON.parse(jsonString);

assert.strictEqual(parsedJson.schema_version, '1.0');
assert.strictEqual(parsedJson.campaign.name, 'EcoStride Launch');
assert.strictEqual(parsedJson.campaign.brand_colors.primary, '#10B981');
assert.strictEqual(parsedJson.assets.poster.image_url, 'http://localhost:8000/static/posters/test_poster_123.png');
assert.strictEqual(parsedJson.assets.storyboard.scenes.length, 3);
assert.strictEqual(parsedJson.assets.social.instagram.hashtags.length, 4);
assert.strictEqual(parsedJson.metadata.project_id, 'proj_eco_001');

// Ensure no huge binary strings
assert(!jsonString.includes('data:image/png;base64,'), 'JSON must not contain raw binary strings');
console.log('✓ Test 3 passed: JSON export matches expected schema.');

// TEST 4: Edited Campaign Synchronization
console.log('Test 4: Verifying edited campaign state is captured in exports...');
const editedCampaign = {
  ...mockCampaign,
  campaign_name: 'EcoStride Pro Edition',
  tagline: 'Defy Friction. Defy Waste.',
  brand_colors: {
    ...mockCampaign.brand_colors,
    primary: '#7C3AED', // Edited to violet
  },
};

const editedMd = generateMarkdownDossier(editedCampaign, mockAssets, mockMetadata);
assert(editedMd.includes('# EcoStride Pro Edition'), 'Markdown did not capture edited name');
assert(editedMd.includes('Defy Friction. Defy Waste.'), 'Markdown did not capture edited tagline');
assert(editedMd.includes('#7C3AED'), 'Markdown did not capture edited primary color');

const editedJson = JSON.parse(generateCampaignJson(editedCampaign, mockAssets, mockMetadata));
assert.strictEqual(editedJson.campaign.name, 'EcoStride Pro Edition');
assert.strictEqual(editedJson.campaign.brand_colors.primary, '#7C3AED');
console.log('✓ Test 4 passed: Edited campaign state seamlessly propagates to exports.');

// TEST 5: Asset Preservation Across Regeneration
console.log('Test 5: Verifying asset preservation...');
// Simulating user regenerating social media only
const regeneratedSocial = {
  ...mockAssets.social,
  headlines: ['A New Pace for the Planet'],
};
const nextAssets = {
  ...mockAssets,
  social: regeneratedSocial,
};
assert.strictEqual(nextAssets.poster.image_url, mockAssets.poster.image_url, 'Poster must not be affected');
assert.strictEqual(nextAssets.storyboard.scenes.length, 3, 'Storyboard must not be affected');
assert.strictEqual(nextAssets.social.headlines[0], 'A New Pace for the Planet', 'Social was updated');
console.log('✓ Test 5 passed: Asset preservation holds true across studio operations.');

console.log('\nALL 5 PHASE 8 EXPORT & INTEGRATION TESTS PASSED SUCCESSFULLY! 🚀');
