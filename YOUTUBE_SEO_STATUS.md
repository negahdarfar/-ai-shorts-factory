# YouTube SEO implementation status

## Implemented in this branch

The Shorts workflow now creates one structured SEO metadata draft per selected topic using the existing `GEMINI_API_KEY` secret and writes `seo_metadata.json` as a workflow artifact.

Each draft contains:
- Primary and secondary keyword ideas
- An accurate, curiosity-led English title
- A readable description
- A small set of relevant hashtags
- Relevant YouTube tags
- A pinned-comment prompt
- A thumbnail concept
- Search intent
- A flag that the draft must be reviewed against the final script

The generator deliberately uses topic-only input at this stage. It does not pretend to have seen the finished video or its final narration. Review and refine the metadata against the generated script before public publishing.

## Not yet implemented

These are separate features and must not be described as already active:
- Live YouTube search-volume or keyword-difficulty research
- YouTube competitor/channel/video analysis and topic-gap scoring
- Google Search keyword/SERP research
- Automatic thumbnail image rendering and YouTube thumbnail upload
- Applying the SEO manifest to a public YouTube upload (the current uploader remains private QA only)
- YouTube Analytics ingestion, CTR/retention analysis, and feedback-based optimization
- Chapters/timestamps for long-form documentaries (chapters are not applicable to Shorts)
- Multilingual metadata/localized titles and descriptions

## Planned production integration

Before enabling public publishing, the public uploader should consume `seo_metadata.json` and apply the title, description, tags, language, category, and appropriate disclosure fields to the matching video. The matching must use a stable video/job ID, not array order alone.

For long-form documentaries, generate chapter timestamps from the final edited timeline/transcript, then validate that timestamps are increasing, start at 00:00, and meet YouTube chapter requirements.

## Ranking and quality safeguards

Metadata can improve relevance and presentation, but cannot guarantee rankings. Prioritize accurate topic satisfaction, strong opening, viewer retention, and audience response. Never stuff keywords, misrepresent the video, or use unrelated trending terms. Shorts discovery is not driven by tags alone.


## Added in the follow-up iteration

A public competitor-research script now queries YouTube Data API v3 for recent Shorts matching each planned topic, retrieves public video statistics, and writes `youtube_competitor_research.json`. The SEO drafting step can use this partial sample to seek a differentiated angle.

Required optional repository secret:
- `YOUTUBE_API_KEY`: a Google API key with YouTube Data API v3 enabled. If it is absent, competitor research is skipped and the SEO draft step still runs.

Interpretation safeguards:
- Search results ordered by view count are only a partial sample, not total market coverage.
- Public view/like/comment counts do not reveal impressions, CTR, retention, watch time, or keyword search volume.
- This research is not a keyword difficulty score and does not predict rankings.
- The workflow stores the report as an artifact for review.
