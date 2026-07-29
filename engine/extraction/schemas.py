from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """Single entity as returned by the LLM."""
    name: str = Field(description="Canonical name of the entity. E.g. 'Elon Musk'")
    entity_type: str = Field(
        description="Category: PERSON, ORGANIZATION, LOCATION, EVENT, PRODUCT, CONCEPT, REGULATION, or OTHER"
    )
    description: str = Field(
        description="1-2 sentence description of this entity in context"
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names, abbreviations, or pronouns that refer to the same entity"
    )

class ExtractedRelation(BaseModel):
    """Single relation as returned by the LLM."""
    source: str = Field(description="Name of the source entity (must match an extracted entity name)")
    target: str = Field(description="Name of the target entity (must match an extracted entity name)")
    relation: str = Field(
        description="Short predicate. E.g. 'founded', 'acquired', 'caused', 'opposed', 'works_for'"
    )

class ExtractionResult(BaseModel):
    """Top-level schema we force the LLM to emit."""
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)