"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-08
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE accounts (
            account_id BIGINT GENERATED ALWAYS AS IDENTITY,
            login TEXT NOT NULL,
            display_name TEXT NOT NULL,
            email TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT pk_accounts PRIMARY KEY (account_id),
            CONSTRAINT uq_accounts_login UNIQUE (login),
            CONSTRAINT ck_accounts_login_not_blank
                CHECK (btrim(login) <> ''),
            CONSTRAINT ck_accounts_display_name_not_blank
                CHECK (btrim(display_name) <> ''),
            CONSTRAINT ck_accounts_email_not_blank
                CHECK (email IS NULL OR btrim(email) <> '')
        );


        CREATE TABLE boards (
            board_id BIGINT GENERATED ALWAYS AS IDENTITY,
            created_by_account_id BIGINT NOT NULL,
            board_label TEXT NOT NULL,
            serial_number TEXT,
            board_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT pk_boards PRIMARY KEY (board_id),

            CONSTRAINT fk_boards_created_by_account
                FOREIGN KEY (created_by_account_id)
                REFERENCES accounts(account_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,

            CONSTRAINT ck_boards_label_not_blank
                CHECK (btrim(board_label) <> ''),

            CONSTRAINT ck_boards_serial_number_not_blank
                CHECK (
                    serial_number IS NULL
                    OR btrim(serial_number) <> ''
                )
        );


        CREATE TABLE images (
            image_id BIGINT GENERATED ALWAYS AS IDENTITY,
            board_id BIGINT NOT NULL,
            uploaded_by_account_id BIGINT NOT NULL,
            storage_key TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            file_size BIGINT,
            file_hash TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT pk_images PRIMARY KEY (image_id),
            CONSTRAINT uq_images_storage_key UNIQUE (storage_key),

            CONSTRAINT fk_images_board
                FOREIGN KEY (board_id)
                REFERENCES boards(board_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,

            CONSTRAINT fk_images_uploaded_by_account
                FOREIGN KEY (uploaded_by_account_id)
                REFERENCES accounts(account_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,

            CONSTRAINT ck_images_storage_key_not_blank
                CHECK (btrim(storage_key) <> ''),

            CONSTRAINT ck_images_original_filename_not_blank
                CHECK (btrim(original_filename) <> ''),

            CONSTRAINT ck_images_mime_type_not_blank
                CHECK (btrim(mime_type) <> ''),

            CONSTRAINT ck_images_file_size_positive
                CHECK (
                    file_size IS NULL
                    OR file_size > 0
                ),

            CONSTRAINT ck_images_file_hash_not_blank
                CHECK (
                    file_hash IS NULL
                    OR btrim(file_hash) <> ''
                )
        );


        CREATE TABLE model_versions (
            model_version_id BIGINT GENERATED ALWAYS AS IDENTITY,
            model_name TEXT NOT NULL,
            version_name TEXT NOT NULL,
            weights_hash TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT pk_model_versions PRIMARY KEY (model_version_id),

            CONSTRAINT uq_model_versions_name_version
                UNIQUE (model_name, version_name),

            CONSTRAINT ck_model_versions_model_name_not_blank
                CHECK (btrim(model_name) <> ''),

            CONSTRAINT ck_model_versions_version_name_not_blank
                CHECK (btrim(version_name) <> ''),

            CONSTRAINT ck_model_versions_weights_hash_not_blank
                CHECK (
                    weights_hash IS NULL
                    OR btrim(weights_hash) <> ''
                )
        );


        CREATE TABLE defect_types (
            defect_type_id BIGINT GENERATED ALWAYS AS IDENTITY,
            defect_code TEXT NOT NULL,
            defect_name TEXT NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            CONSTRAINT pk_defect_types PRIMARY KEY (defect_type_id),
            CONSTRAINT uq_defect_types_code UNIQUE (defect_code),

            CONSTRAINT ck_defect_types_code_not_blank
                CHECK (btrim(defect_code) <> ''),

            CONSTRAINT ck_defect_types_name_not_blank
                CHECK (btrim(defect_name) <> ''),

            CONSTRAINT ck_defect_types_code_format
                CHECK (
                    defect_code ~ '^[a-z0-9][a-z0-9_]*$'
                )
        );


        CREATE TABLE analysis_requests (
            analysis_request_id BIGINT GENERATED ALWAYS AS IDENTITY,
            account_id BIGINT NOT NULL,
            image_id BIGINT NOT NULL,
            request_status TEXT NOT NULL DEFAULT 'created',
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            error_code TEXT,
            error_message TEXT,

            CONSTRAINT pk_analysis_requests
                PRIMARY KEY (analysis_request_id),

            CONSTRAINT fk_analysis_requests_account
                FOREIGN KEY (account_id)
                REFERENCES accounts(account_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,

            CONSTRAINT fk_analysis_requests_image
                FOREIGN KEY (image_id)
                REFERENCES images(image_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,

            CONSTRAINT ck_analysis_requests_status
                CHECK (
                    request_status IN (
                        'created',
                        'processing',
                        'completed',
                        'failed'
                    )
                ),

            CONSTRAINT ck_analysis_requests_started_after_created
                CHECK (
                    started_at IS NULL
                    OR started_at >= created_at
                ),

            CONSTRAINT ck_analysis_requests_finished_after_created
                CHECK (
                    finished_at IS NULL
                    OR finished_at >= created_at
                ),

            CONSTRAINT ck_analysis_requests_finished_after_started
                CHECK (
                    finished_at IS NULL
                    OR started_at IS NULL
                    OR finished_at >= started_at
                ),

            CONSTRAINT ck_analysis_requests_error_code_not_blank
                CHECK (
                    error_code IS NULL
                    OR btrim(error_code) <> ''
                ),

            CONSTRAINT ck_analysis_requests_error_message_not_blank
                CHECK (
                    error_message IS NULL
                    OR btrim(error_message) <> ''
                ),

            CONSTRAINT ck_analysis_requests_state_consistency
                CHECK (
                    (
                        request_status = 'created'
                        AND started_at IS NULL
                        AND finished_at IS NULL
                        AND error_code IS NULL
                        AND error_message IS NULL
                    )
                    OR
                    (
                        request_status = 'processing'
                        AND started_at IS NOT NULL
                        AND finished_at IS NULL
                        AND error_code IS NULL
                        AND error_message IS NULL
                    )
                    OR
                    (
                        request_status = 'completed'
                        AND started_at IS NOT NULL
                        AND finished_at IS NOT NULL
                        AND error_code IS NULL
                        AND error_message IS NULL
                    )
                    OR
                    (
                        request_status = 'failed'
                        AND finished_at IS NOT NULL
                        AND error_code IS NOT NULL
                    )
                )
        );


        CREATE TABLE analyses (
            analysis_id BIGINT GENERATED ALWAYS AS IDENTITY,
            analysis_request_id BIGINT NOT NULL,
            model_version_id BIGINT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT pk_analyses PRIMARY KEY (analysis_id),

            CONSTRAINT uq_analyses_analysis_request
                UNIQUE (analysis_request_id),

            CONSTRAINT fk_analyses_analysis_request
                FOREIGN KEY (analysis_request_id)
                REFERENCES analysis_requests(analysis_request_id)
                ON UPDATE RESTRICT
                ON DELETE CASCADE,

            CONSTRAINT fk_analyses_model_version
                FOREIGN KEY (model_version_id)
                REFERENCES model_versions(model_version_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT
        );


        CREATE TABLE detections (
            detection_id BIGINT GENERATED ALWAYS AS IDENTITY,
            analysis_id BIGINT NOT NULL,
            defect_type_id BIGINT NOT NULL,

            confidence DOUBLE PRECISION NOT NULL,

            bbox_x DOUBLE PRECISION NOT NULL,
            bbox_y DOUBLE PRECISION NOT NULL,
            bbox_width DOUBLE PRECISION NOT NULL,
            bbox_height DOUBLE PRECISION NOT NULL,

            CONSTRAINT pk_detections PRIMARY KEY (detection_id),

            CONSTRAINT fk_detections_analysis
                FOREIGN KEY (analysis_id)
                REFERENCES analyses(analysis_id)
                ON UPDATE RESTRICT
                ON DELETE CASCADE,

            CONSTRAINT fk_detections_defect_type
                FOREIGN KEY (defect_type_id)
                REFERENCES defect_types(defect_type_id)
                ON UPDATE RESTRICT
                ON DELETE RESTRICT,

            CONSTRAINT ck_detections_confidence
                CHECK (
                    confidence >= 0.0
                    AND confidence <= 1.0
                ),

            CONSTRAINT ck_detections_bbox_x
                CHECK (
                    bbox_x >= 0.0
                    AND bbox_x <= 1.0
                ),

            CONSTRAINT ck_detections_bbox_y
                CHECK (
                    bbox_y >= 0.0
                    AND bbox_y <= 1.0
                ),

            CONSTRAINT ck_detections_bbox_width
                CHECK (
                    bbox_width > 0.0
                    AND bbox_width <= 1.0
                ),

            CONSTRAINT ck_detections_bbox_height
                CHECK (
                    bbox_height > 0.0
                    AND bbox_height <= 1.0
                ),

            CONSTRAINT ck_detections_bbox_horizontal_bounds
                CHECK (
                    bbox_x + bbox_width <= 1.0
                ),

            CONSTRAINT ck_detections_bbox_vertical_bounds
                CHECK (
                    bbox_y + bbox_height <= 1.0
                )
        );


        CREATE FUNCTION set_updated_at()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at := CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$;


        CREATE TRIGGER trg_accounts_set_updated_at
        BEFORE UPDATE ON accounts
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();


        CREATE TRIGGER trg_boards_set_updated_at
        BEFORE UPDATE ON boards
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();


        CREATE INDEX ix_boards_created_by_account_created_at
            ON boards (
                created_by_account_id,
                created_at DESC
            );

        CREATE INDEX ix_images_board_created_at
            ON images (
                board_id,
                created_at DESC
            );

        CREATE INDEX ix_images_uploaded_by_account
            ON images (
                uploaded_by_account_id
            );

        CREATE INDEX ix_analysis_requests_account_created_at
            ON analysis_requests (
                account_id,
                created_at DESC
            );

        CREATE INDEX ix_analysis_requests_image_created_at
            ON analysis_requests (
                image_id,
                created_at DESC
            );

        CREATE INDEX ix_analysis_requests_status_created_at
            ON analysis_requests (
                request_status,
                created_at DESC
            );

        CREATE INDEX ix_analyses_model_version
            ON analyses (
                model_version_id
            );

        CREATE INDEX ix_detections_analysis
            ON detections (
                analysis_id
            );

        CREATE INDEX ix_detections_defect_type
            ON detections (
                defect_type_id
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_boards_set_updated_at ON boards;
        DROP TRIGGER IF EXISTS trg_accounts_set_updated_at ON accounts;
        DROP FUNCTION IF EXISTS set_updated_at();

        DROP TABLE IF EXISTS detections;
        DROP TABLE IF EXISTS analyses;
        DROP TABLE IF EXISTS analysis_requests;
        DROP TABLE IF EXISTS defect_types;
        DROP TABLE IF EXISTS model_versions;
        DROP TABLE IF EXISTS images;
        DROP TABLE IF EXISTS boards;
        DROP TABLE IF EXISTS accounts;
        """
    )