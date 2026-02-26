from sqlalchemy import JSON, BigInteger, Boolean, Column, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class MV_LocationShortLatestMetrics(Base):

    __tablename__ = "mv_location_short_latest_metrics"

    id = Column(Integer, primary_key=True)  # суррогатный первичный ключ
    country_id = Column(Integer, nullable=True)
    city_id = Column(Integer, nullable=True)
    metric_id = Column(Integer)
    preset_id = Column(Integer)
    series_id = Column(Integer)
    period_year = Column(Integer)
    attributes = Column(JSON)
    value_numeric = Column(Float)
    value_string = Column(String)
    value_boolean = Column(Boolean)
    value_range_start = Column(Float)
    value_range_end = Column(Float)
