from typing import Annotated, Union, TypeVar, List
import typing
from pydantic import create_model, BaseModel, Field
from loguru import logger

Model = TypeVar('Model', bound='BaseModel')


class DyntamicFactory:

    TYPES = {
        'string': str,
        'array': list,
        'boolean': bool,
        'integer': int,
        'float': float,
        'number': float,
    }

    def __init__(self,
                 json_schema: dict,
                 base_model: typing.Union[type[Model], typing.Tuple[type[Model], ...], None] = None,
                 ref_template: str = "$defs"
                 ) -> None:
        self.class_name = json_schema.get('title')
        self.class_type = json_schema.get('type')
        self.required = json_schema.get('required', False)
        self.raw_fields = json_schema.get('properties')
        logger.info("Fields" + str(self.raw_fields))
        self.ref_template = ref_template
        logger.info(self.ref_template)
        self.definitions = json_schema.get(ref_template)
        logger.info(self.definitions)
        self.fields = {}
        self.model_fields = {}
        self._base_model = base_model

    def make(self) -> Model:
        for field, field_schema in self.raw_fields.items():
            if '$ref' in str(field_schema):
                model_name = field_schema.get('items').get('$ref').strip('#/').split('/')[-1]
                if model_name in self.definitions:
                    self._make_nested(model_name, field)
            else:
                factory = self.TYPES.get(field_schema.get('type'))
                if factory == list:
                    items = field_schema.get('items')
                    if self.ref_template in items:
                        self._make_nested(items.get(self.ref_template), field)
                description = field_schema.get('description')
                self._make_field(factory, field, field_schema.get('title'), description)
        return create_model(self.class_name, __base__=self._base_model, **self.model_fields)

    def _make_nested(self, model_name: str, field: str) -> None:
        level = DyntamicFactory({self.ref_template: self.definitions} | self.definitions.get(model_name),
                                ref_template=self.ref_template)
        level.make()
        model = create_model(model_name, **level.model_fields)
        self._make_field(model, field, field, None, field_type="array", items=model_name)

    def _make_field(self, factory, field, alias, description, items=None, field_type=None) -> None:
        if field not in self.required:
            factory_annotation = Annotated[Union[factory | None], factory]
        else:
            factory_annotation = factory
        if description:
            field_instance = Field(default_factory=factory, alias=alias, description=description)
        else:
            field_instance = Field(default_factory=factory, alias=alias)
        if items:
            field_instance = Field(..., alias=alias, description=description, items=items, type=field_type)
        self.model_fields[field] = (Annotated[factory_annotation, field_instance], ...)





'''

 {'$defs': {'StorageUnitInformation': {'properties': {'price': {'description': 'Price for the storage unit, in dollars.', 'title': 'Price', 'type': 'integer'}, 'square_feet': {'description': 'Size of the storage unit, in square feet. ex) 25sqft', 'title': 'Square Feet', 'type': 'integer'}, 'dimension': {'description': 'Dimension ex) 5x5 of the storage unit.', 'title': 'Dimension', 'type': 'string'}, 'metadata': {'description': 'Additional metadata about the storage unit, such as location or features.', 'title': 'Metadata', 'type': 'string'}}, 'required': ['price', 'square_feet', 'dimension', 'metadata'], 'title': 'StorageUnitInformation', 'type': 'object'}}, 'properties': {'storage_units': {'description': 'A list of all the different storage unit offerings on the given page including just the fields in the StorageUnitInformation model.', 'items': {'$ref': '#/$defs/StorageUnitInformation'}, 'title': 'Storage Units', 'type': 'array'}}, 'required': ['storage_units'], 'title': 'InformationList', 'type': 'object'}
'''
async def test_dynamic_factory():
    class StorageUnitInformation(BaseModel):
        price: int = Field(..., description="Price for the storage unit, in dollars.")
        square_feet: int = Field(..., description="Size of the storage unit, in square feet. ex) 25sqft")
        dimension: str = Field(..., description="Dimension ex) 5x5 of the storage unit.")
        metadata: str = Field(..., description="Additional metadata about the storage unit, such as location or features.")
    class InformationList(BaseModel):
        storage_units: List[StorageUnitInformation] = Field(..., description="A list of all the different storage unit offerings on the given page including just the fields in the StorageUnitInformation model.")
    model_schema = InformationList.model_json_schema()
    

    dyn_schema = DyntamicFactory(model_schema, ref_template="$defs")
    model = dyn_schema.make()
    model_schema2 = model.model_json_schema()
    logger.info(model_schema)
    logger.info(model_schema2)
    assert model.schema() == InformationList.schema()

async def test_simple_dynamic_factory():
    class SimpleModel(BaseModel):
        name: str = Field(..., description="Name of the entity.")
    model_schema = SimpleModel.model_json_schema()

    dyn_schema = DyntamicFactory(model_schema, ref_template="$defs")
    model = dyn_schema.make()
    model_schema2 = model.model_json_schema()
    logger.info(model_schema)
    logger.info(model_schema2)
    assert model.schema() == SimpleModel.schema()


if __name__ == "__main__":
    import asyncio

    #asyncio.run(test_dynamic_factory())
    asyncio.run(test_simple_dynamic_factory())
