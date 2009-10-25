"""
Test the basic Entity object
"""

import unittest
from clusto.test import testbase
import datetime

import clusto
from clusto.schema import *

class TestEntitySchema(testbase.ClustoTestBase):

    def testCreateEntityObject(self):

        e1 = Entity('e1')
        e2 = Entity('e2')

        clusto.flush()

        res = SESSION.query(Entity).filter_by(name='e1')

        self.assertEqual(res.count(),1)

        e = res.all()[0]

        self.assertEqual(e.name, 'e1')


    def testOutputEntityObject(self):

        expectedout = "e1"
        
        e1 = Entity('e1')

        self.assertEqual(str(e1), expectedout)

        clusto.flush()

        self.assertEqual(str(SESSION.query(Entity).filter_by(name='e1')[0]), expectedout)
        

    def testDeleteEntity(self):

        e1 = Entity('e1')

        clusto.flush()

        self.assertEqual(SESSION.query(Entity).filter_by(type='entity').count(), 1)

        e1.delete()

        clusto.flush()

        self.assertEqual(SESSION.query(Entity).filter_by(type='entity').count(), 0)
    
class TestEntityAttributes(testbase.ClustoTestBase):

    def data(self):

        Entity('e1')
        Entity('e2')
        Entity('e3')

        clusto.flush()

    def testAddingAttribute(self):

        e = SESSION.query(Entity).filter_by(name='e2').one()

        e1 = SESSION.query(Entity).filter_by(name='e1').one()

                
        self.assertEqual(e.name, 'e2')

        e.add_attr(key='one', value=1)
        e.add_attr(key='two', value=2)

        clusto.flush()

        q = SESSION.query(Attribute).filter_by(entity_id=e.entity_id,
                                               key='two').one() 
        self.assertEqual(q.value, 2)

        q = SESSION.query(Attribute).filter_by(entity_id=e.entity_id,
                                               key='one').one()

        self.assertEqual(q.value, 1)
        

    def testAddingDateAttribute(self):

        e1 = SESSION.query(Entity).filter_by(name='e1').one()

        d = datetime.datetime(2007,12,16,7,46)
        
        e1.add_attr('somedate', d)

        clusto.flush()

        q = SESSION.query(Attribute).filter_by(entity_id=e1.entity_id,
                                               key='somedate').one()

        self.assertEqual(q.value, d)
        
    def testData(self):

        q = SESSION.query(Entity).\
               filter(not_(Entity.type=='clustometa')).count()

        self.assertEqual(q, 3)
        
    def testEmptyAttributes(self):
        """
        If I set no attributes there shouldn't be any in the DB except the
        clusto meta attributes
        """
        
        q = SESSION.query(Attribute).join('entity').\
               filter(not_(Entity.type=='clustometa')).count()

        self.assertEqual(q, 0)
        
    def testRelationAttribute(self):

        e1 = SESSION.query(Entity).filter_by(name='e1').one()
        
        e4 = Entity('e4')
        e4.add_attr(key='e1', value=e1)
        
        clusto.flush()


        e4 = SESSION.query(Entity).filter_by(name='e4').one()

        attr = e4._attrs[0]

        self.assertEqual(attr.relation_value, e1)

    def testStringAttribute(self):

        e2 = SESSION.query(Entity).filter_by(name='e2').one()

        e2.add_attr(key='somestring', value='thestring')

        clusto.flush()

        q = SESSION.query(Attribute).filter_by(entity=e2,
                                               key='somestring').one()

        self.assertEqual(q.value, 'thestring')

    def testIntAttribute(self):

        e4 = Entity('e4')
        e4.add_attr(key='someint', value=10)

        clusto.flush()

        q = SESSION.query(Attribute).filter_by(entity=e4,
                                               key='someint').one()

        self.assertEqual(q.value, 10)

    def testMultipleAttributes(self):

        e2 = SESSION.query(Entity).filter_by(name='e2').one()

        e2.add_attr(key='somestring', number=1, subkey='foo',
                                   value='thestring')

        e2.add_attr(key='somestring', number=1, subkey='foo',
                                   value='thestring')


        clusto.flush()

        q = SESSION.query(Attribute).filter_by(entity=e2,
                                               key='somestring').all()

        self.assertEqual([a.value for a in q], 
                         ['thestring', 'thestring'])

    def testEntityDeleteRelations(self):

        e1 = SESSION.query(Entity).filter_by(name='e1').one()
        e2 = SESSION.query(Entity).filter_by(name='e2').one()

        e1.add_attr('pointer1', e2)

        clusto.flush()

        self.assertEqual(SESSION.query(Entity).\
                            filter_by(type='entity').count(),
                         3)

        self.assertEqual(SESSION.query(Attribute).\
                            filter(and_(Entity.entity_id==Attribute.entity_id,
                                        Entity.type=='entity')).count()
                         , 1)

        e2new = SESSION.query(Entity).filter_by(name='e2').one()

        e2new.delete()

        self.assertEqual(SESSION.query(Entity).\
                            filter_by(type='entity').count(),
                         2)
        
        self.assertEqual(SESSION.query(Attribute).\
                            filter(and_(Entity.entity_id==Attribute.entity_id,
                                        Entity.type=='entity')).count(),
                         0)

        clusto.flush()

        self.assertEqual(SESSION.query(Entity).\
                            filter_by(type='entity').count(),
                         2)
        self.assertEqual(SESSION.query(Attribute).\
                            filter(and_(Entity.entity_id==Attribute.entity_id,
                                        Entity.type=='entity')).count(),
                         0)


    def testAccessRelationAttributesMultipleTimes(self):
        e1 = SESSION.query(Entity).filter_by(name='e1').one()
        e2 = SESSION.query(Entity).filter_by(name='e2').one()

        e1.add_attr('foo', 2)
        e1.add_attr('foo', e2)

        clusto.flush()
        e1 = SESSION.query(Entity).filter_by(name='e1').one()
        self.assertEqual(len(list(e1._attrs)), 2)
        self.assertEqual(len(list(e1._attrs)), 2)
        self.assertEqual(len(list(e1._attrs)), 2)

        
    
class TestEntityReferences(testbase.ClustoTestBase):

    def data(self):
        
        e1 = Entity('e1')
        e2 = Entity('e2')
        e3 = Entity('e3')

        e3.add_attr(key='e1', value=e1)
        e3.add_attr(key='e2', value=e2)

        clusto.flush()
    
    def testReference(self):

        e1 = SESSION.query(Entity).filter_by(name='e1').one()
        e2 = SESSION.query(Entity).filter_by(name='e2').one()
        e3 = SESSION.query(Entity).filter_by(name='e3').one()

        self.assertEqual(e1._references[0].entity,
                         e2._references[0].entity)

        self.assertEqual(e3,
                         e2._references[0].entity)

    def testReferenceDelete(self):

        e1 = SESSION.query(Entity).filter_by(name='e1').one()


        e3 = SESSION.query(Entity).filter_by(name='e3').one()

        
        e3.delete()


        self.assertEqual(len(list(e1._references)), 0)

        clusto.flush()

        e1a = SESSION.query(Entity).filter_by(name='e1').one()

        self.assertEqual(len(list(e1a._references)), 0)
        self.assertEqual(id(e1a), id(e1))

        e2 = SESSION.query(Entity).filter_by(name='e2').one()

        self.assertEqual(len(list(e2._references)), 0)

