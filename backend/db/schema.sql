-- Enable LTREE extension for hierarchical data
CREATE EXTENSION IF NOT EXISTS ltree;

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table - supports hierarchical structure
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL, -- User-friendly title, any characters allowed
    description TEXT,
    priority VARCHAR(20) CHECK (priority IN ('high', 'medium', 'low')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked')),
    parent_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
    path LTREE, -- IMPORTANT: Use ONLY numeric IDs in the path (e.g., '1.2.3') due to LTREE character limitations
    color_code VARCHAR(9), -- Reduced to 9 chars to accommodate #RRGGBBAA format
    estimated_duration INTEGER, -- Estimated duration in seconds or pomodoro count
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ, -- Added completion time field
    deleted_at TIMESTAMPTZ, -- Soft delete support
    CONSTRAINT valid_parent CHECK (parent_id != id)
);

-- Pomodoro sessions table
CREATE TABLE pomodoro_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    duration INTEGER NOT NULL, -- Planned duration in seconds
    actual_duration INTEGER, -- Actual duration in seconds
    session_type VARCHAR(20) NOT NULL CHECK (session_type IN ('work', 'short_break', 'long_break')),
    completed BOOLEAN DEFAULT FALSE,
    interruption_reason TEXT, -- Added field to track why a session was interrupted
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ, -- Added soft delete support
    CONSTRAINT valid_time_range CHECK (end_time IS NULL OR end_time > start_time)
);

-- Pomodoro-task association table - implements decoupling
CREATE TABLE pomodoro_task_associations (
    id SERIAL PRIMARY KEY,
    pomodoro_session_id INTEGER NOT NULL REFERENCES pomodoro_sessions(id) ON DELETE CASCADE,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    time_spent INTEGER, -- Time spent on this task (seconds)
    notes TEXT, -- Notes about the task during this session
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ -- Added soft delete support
);

-- Create ENUM type for task actions
CREATE TYPE task_action AS ENUM (
    'created', 
    'updated',
    'soft_deleted', 
    'restored'
);

-- Task history table - for visual history feature
CREATE TABLE task_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action task_action NOT NULL, -- Using ENUM type for consistency
    changes JSONB NOT NULL, -- Stores all changes including old and new values
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- User settings table
CREATE TABLE user_settings (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    pomodoro_duration INTEGER DEFAULT 1500, -- 25 minutes in seconds
    short_break_duration INTEGER DEFAULT 300, -- 5 minutes
    long_break_duration INTEGER DEFAULT 900, -- 15 minutes
    pomodoros_until_long_break INTEGER DEFAULT 4,
    theme VARCHAR(20) DEFAULT 'light',
    notification_enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX tasks_user_id_idx ON tasks(user_id);
CREATE INDEX tasks_parent_id_idx ON tasks(parent_id);
CREATE INDEX tasks_path_idx ON tasks USING GIST(path);
CREATE INDEX tasks_status_idx ON tasks(status);
CREATE INDEX tasks_completed_at_idx ON tasks(completed_at); -- Added index for completed_at

-- Improved index for non-deleted tasks (common case)
CREATE INDEX tasks_not_deleted_idx ON tasks(user_id, parent_id, status) WHERE deleted_at IS NULL;

CREATE INDEX pomodoro_user_id_idx ON pomodoro_sessions(user_id);
CREATE INDEX pomodoro_time_idx ON pomodoro_sessions(start_time);
CREATE INDEX pomodoro_not_deleted_idx ON pomodoro_sessions(user_id) WHERE deleted_at IS NULL;

CREATE INDEX task_history_user_id_idx ON task_history(user_id);
CREATE INDEX task_history_task_id_idx ON task_history(task_id);
CREATE INDEX task_history_action_idx ON task_history(action);

CREATE INDEX pomodoro_task_assoc_pomodoro_idx ON pomodoro_task_associations(pomodoro_session_id);
CREATE INDEX pomodoro_task_assoc_task_idx ON pomodoro_task_associations(task_id);
CREATE INDEX pomodoro_task_assoc_not_deleted_idx ON pomodoro_task_associations(pomodoro_session_id, task_id) 
    WHERE deleted_at IS NULL;

-- Trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- Trigger to update task path using LTREE with circular reference check
CREATE OR REPLACE FUNCTION update_task_path()
RETURNS TRIGGER AS $$
DECLARE
    parent_path LTREE;
BEGIN
    IF NEW.parent_id IS NULL THEN
        NEW.path = text2ltree(NEW.id::TEXT);
    ELSE
        SELECT path INTO parent_path FROM tasks WHERE id = NEW.parent_id;
        IF parent_path IS NULL THEN
            RAISE EXCEPTION 'Parent task with ID % not found or has no path', NEW.parent_id;
        END IF;
        
        -- Add circular reference check
        IF NEW.id IS NOT NULL AND parent_path <@ text2ltree(NEW.id::TEXT) THEN
            RAISE EXCEPTION 'Circular reference detected: task % cannot be a child of %', NEW.id, NEW.parent_id;
        END IF;
        
        NEW.path = parent_path || text2ltree(NEW.id::TEXT);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_task_path
BEFORE INSERT ON tasks
FOR EACH ROW
EXECUTE FUNCTION update_task_path();

-- Trigger to update task path when parent_id changes with circular reference check
CREATE OR REPLACE FUNCTION update_task_path_on_parent_change()
RETURNS TRIGGER AS $$
DECLARE
    parent_path LTREE;
    old_subpath LTREE;
    new_subpath LTREE;
BEGIN
    -- Only proceed if parent_id has changed
    IF OLD.parent_id IS NOT DISTINCT FROM NEW.parent_id THEN
        RETURN NEW;
    END IF;
    
    -- Calculate the new path
    IF NEW.parent_id IS NULL THEN
        NEW.path = text2ltree(NEW.id::TEXT);
    ELSE
        SELECT path INTO parent_path FROM tasks WHERE id = NEW.parent_id;
        IF parent_path IS NULL THEN
            RAISE EXCEPTION 'Parent task with ID % not found or has no path', NEW.parent_id;
        END IF;
        
        -- Add circular reference check
        IF parent_path <@ text2ltree(NEW.id::TEXT) THEN
            RAISE EXCEPTION 'Circular reference detected: task % cannot be a child of %', NEW.id, NEW.parent_id;
        END IF;
        
        NEW.path = parent_path || text2ltree(NEW.id::TEXT);
    END IF;
    
    -- Update paths of all descendant tasks
    old_subpath := OLD.path;
    new_subpath := NEW.path;
    
    UPDATE tasks
    SET path = new_subpath || subpath(path, nlevel(old_subpath))
    WHERE path <@ old_subpath AND id != NEW.id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_task_path_on_parent_change
BEFORE UPDATE ON tasks
FOR EACH ROW
WHEN (OLD.parent_id IS DISTINCT FROM NEW.parent_id)
EXECUTE FUNCTION update_task_path_on_parent_change();

-- Trigger to update completed_at when status changes to/from 'completed'
CREATE OR REPLACE FUNCTION update_task_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    ELSIF NEW.status != 'completed' AND OLD.status = 'completed' THEN
        NEW.completed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_task_completed_at
BEFORE UPDATE ON tasks
FOR EACH ROW
WHEN (NEW.status IS DISTINCT FROM OLD.status)
EXECUTE FUNCTION update_task_completed_at();

-- Trigger to log task history using JSONB
CREATE OR REPLACE FUNCTION log_task_history()
RETURNS TRIGGER AS $$
DECLARE
    changes JSONB := '{}'::JSONB;
    old_record JSONB;
    new_record JSONB;
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO task_history(task_id, user_id, action, changes)
        VALUES(NEW.id, NEW.user_id, 'created', to_jsonb(NEW));
        RETURN NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Ensure user ID exists
        IF NEW.user_id IS NULL THEN
            RAISE EXCEPTION 'User ID is required for task history tracking';
        END IF;

        old_record := to_jsonb(OLD);
        new_record := to_jsonb(NEW);
        
        -- Compare all fields and record changes
        SELECT jsonb_object_agg(key, jsonb_build_object('old', old_record->key, 'new', new_record->key))
        INTO changes
        FROM jsonb_object_keys(new_record) key
        WHERE new_record->key IS DISTINCT FROM old_record->key
          AND key != 'updated_at'; -- Ignore automatically updated timestamp
        
        -- Only insert record if there are actual changes
        IF changes <> '{}'::JSONB THEN
            -- Determine the correct action type
            IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
                INSERT INTO task_history(task_id, user_id, action, changes)
                VALUES(NEW.id, NEW.user_id, 'soft_deleted', changes);
            ELSIF OLD.deleted_at IS NOT NULL AND NEW.deleted_at IS NULL THEN
                INSERT INTO task_history(task_id, user_id, action, changes)
                VALUES(NEW.id, NEW.user_id, 'restored', changes);
            ELSE
                INSERT INTO task_history(task_id, user_id, action, changes)
                VALUES(NEW.id, NEW.user_id, 'updated', changes);
            END IF;
        END IF;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger to cascade soft deletes/restores from tasks to associations
CREATE OR REPLACE FUNCTION cascade_task_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- When a task is soft-deleted, cascade soft-delete all its child tasks
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        UPDATE tasks
        SET deleted_at = NEW.deleted_at
        WHERE path <@ OLD.path AND id != OLD.id AND deleted_at IS NULL;
    -- When a task is restored, restore all its child tasks
    ELSIF NEW.deleted_at IS NULL AND OLD.deleted_at IS NOT NULL THEN
        UPDATE tasks
        SET deleted_at = NULL
        WHERE path <@ OLD.path AND id != OLD.id AND deleted_at = OLD.deleted_at;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cascade_task_soft_delete
AFTER UPDATE ON tasks
FOR EACH ROW
WHEN (OLD.deleted_at IS DISTINCT FROM NEW.deleted_at)
EXECUTE FUNCTION cascade_task_soft_delete();

-- Improved trigger for cascading soft deletes/restores from pomodoro sessions to associations
CREATE OR REPLACE FUNCTION cascade_pomodoro_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- When a pomodoro session is soft-deleted, soft-delete all its associations
    IF NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        UPDATE pomodoro_task_associations
        SET deleted_at = NEW.deleted_at
        WHERE pomodoro_session_id = NEW.id AND deleted_at IS NULL;
    -- When a pomodoro session is restored, restore its associations
    ELSIF NEW.deleted_at IS NULL AND OLD.deleted_at IS NOT NULL THEN
        UPDATE pomodoro_task_associations
        SET deleted_at = NULL
        WHERE pomodoro_session_id = NEW.id AND deleted_at = OLD.deleted_at;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER cascade_pomodoro_session_soft_delete
AFTER UPDATE ON pomodoro_sessions
FOR EACH ROW
WHEN (OLD.deleted_at IS DISTINCT FROM NEW.deleted_at)
EXECUTE FUNCTION cascade_pomodoro_soft_delete();

-- Improved function to get task breadcrumb using LTREE
CREATE OR REPLACE FUNCTION get_task_breadcrumb(task_id INTEGER)
RETURNS TABLE(id INTEGER, title VARCHAR, level INTEGER) AS $$
BEGIN
  RETURN QUERY
  SELECT t.id, t.title, nlevel(t.path) - 1 AS level
  FROM tasks t
  WHERE t.path @> (SELECT path FROM tasks WHERE id = task_id)
    AND t.deleted_at IS NULL
  ORDER BY t.path;
END;
$$ LANGUAGE plpgsql;

-- Improved function to get all children of a task using LTREE
CREATE OR REPLACE FUNCTION get_task_children(task_id INTEGER)
RETURNS TABLE(id INTEGER, title VARCHAR, level INTEGER) AS $$
BEGIN
   RETURN QUERY
   SELECT t.id, t.title, nlevel(t.path) - (SELECT nlevel(path) FROM tasks WHERE id = task_id) as level
   FROM tasks t
   WHERE t.path <@ (SELECT path FROM tasks WHERE id = task_id)
      AND t.id <> task_id  -- Exclude the parent task itself
      AND t.deleted_at IS NULL
   ORDER BY t.path;
END;
$$ LANGUAGE plpgsql;

-- Improved function to check if a task is a descendant of another task
CREATE OR REPLACE FUNCTION is_descendant(potential_descendant_id INTEGER, ancestor_id INTEGER)
RETURNS BOOLEAN AS $$
DECLARE
    ancestor_path LTREE;
    descendant_path LTREE;
BEGIN
    -- If IDs are the same, it's not a descendant relationship
    IF potential_descendant_id = ancestor_id THEN
        RETURN FALSE;
    END IF;
    
    SELECT path INTO ancestor_path FROM tasks WHERE id = ancestor_id AND deleted_at IS NULL;
    SELECT path INTO descendant_path FROM tasks WHERE id = potential_descendant_id AND deleted_at IS NULL;
    
    IF ancestor_path IS NULL OR descendant_path IS NULL THEN
        RETURN FALSE;
    END IF;
    
    -- Check if descendant_path contains ancestor_path as a prefix
    -- AND ensure it's a true descendant (not the same node)
    RETURN descendant_path <@ ancestor_path AND nlevel(descendant_path) > nlevel(ancestor_path);
END;
$$ LANGUAGE plpgsql;