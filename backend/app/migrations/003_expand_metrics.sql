/*
  # Expand Metrics Support

  1. Changes
    - Add missing metric columns to aggregates_minute table
    - Add positivity, volatility, distraction, fatigue, risk columns

  2. Why
    - AI module computes 9 metrics but aggregates only stored 4
    - Need full metric tracking for comprehensive analytics

  3. Security
    - No RLS changes needed (aggregates inherit from events security)
*/

-- Add missing metric columns to aggregates_minute
ALTER TABLE aggregates_minute
  ADD COLUMN IF NOT EXISTS avg_positivity FLOAT,
  ADD COLUMN IF NOT EXISTS avg_volatility FLOAT,
  ADD COLUMN IF NOT EXISTS avg_distraction FLOAT,
  ADD COLUMN IF NOT EXISTS avg_fatigue FLOAT,
  ADD COLUMN IF NOT EXISTS avg_risk FLOAT;

-- Create index for risk-based queries (high priority alerts)
CREATE INDEX IF NOT EXISTS idx_aggregates_risk ON aggregates_minute(avg_risk DESC)
  WHERE avg_risk > 0.7;

-- Create index for engagement-based queries (performance tracking)
CREATE INDEX IF NOT EXISTS idx_aggregates_engagement ON aggregates_minute(avg_engagement DESC);
