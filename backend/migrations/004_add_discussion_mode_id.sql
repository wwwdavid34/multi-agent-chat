-- Migration: Add discussion_mode_id column to conversation_messages
-- Created: 2026-01-27
-- Purpose: Track which discussion mode was used for each message

ALTER TABLE conversation_messages
    ADD COLUMN IF NOT EXISTS discussion_mode_id VARCHAR(50);
