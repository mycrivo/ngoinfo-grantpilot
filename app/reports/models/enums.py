import enum


class DonorReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    EXTRACTING = "EXTRACTING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    GENERATING = "GENERATING"
    DEGRADED = "DEGRADED"
    COMPLETE = "COMPLETE"


class ReportingFrequency(str, enum.Enum):
    END_OF_GRANT = "end_of_grant"
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    INTERIM = "interim"
    FINAL = "final"


class DocumentClassification(str, enum.Enum):
    PROPOSAL = "proposal"
    GRANT_LETTER = "grant_letter"
    MOU = "mou"
    INDICATOR_DATA = "indicator_data"
    PHOTO = "photo"
    DECK = "deck"
    OTHER = "other"


class ExtractionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ReportJobStage(str, enum.Enum):
    CLASSIFY = "classify"
    EXTRACT = "extract"
    RECONCILE = "reconcile"
    GAP = "gap"
    SYNTHESISE = "synthesise"
    CRITIQUE = "critique"
    EXPORT = "export"


class ReportJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_HUMAN = "awaiting_human"
    FAILED = "failed"
    DONE = "done"
