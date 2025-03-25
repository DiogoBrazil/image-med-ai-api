from datetime import datetime
import asyncpg
import uuid
from typing import Any, Dict, List, Optional, Tuple
from ..utils.logger import get_logger
from ..db.database import get_database
from ..config.settings import Settings

settings = Settings()
logger = get_logger(__name__)

class AttendanceRepository:
    def __init__(self):
        self.db_connection = get_database()
        self.pool = None

    async def init_pool(self):
        """Initialize the connection pool if necessary."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.db_connection, min_size=1, max_size=10)
            logger.info("Connection pool initialized.")

    async def add_attendance(self, attendance_data: Dict) -> Dict:
        """Add a new attendance record with optional bounding boxes."""
        await self.init_pool()
        

        try:
            professional_id = attendance_data.get("professional_id")
            if isinstance(professional_id, str):
                professional_id = uuid.UUID(professional_id)
                
            health_unit_id = attendance_data.get("health_unit_id")
            if isinstance(health_unit_id, str):
                health_unit_id = uuid.UUID(health_unit_id)
                
            admin_id = attendance_data.get("admin_id")
            if isinstance(admin_id, str):
                admin_id = uuid.UUID(admin_id)
        except ValueError as e:
            logger.error(f"Invalid UUID format in attendance data: {e}")
            return {"attendance_id": "", "added": False}
        

        bounding_boxes = attendance_data.pop("bounding_boxes", [])
        
        try:
            async with self.pool.acquire() as conn:

                async with conn.transaction():

                    query = """
                        INSERT INTO attendances (
                            professional_id, health_unit_id, admin_id, 
                            model_used, model_result, expected_result, correct_diagnosis,
                            image_base64, observations
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) 
                        RETURNING id
                    """
                    
                    returned_id = await conn.fetchval(
                        query,
                        professional_id,
                        health_unit_id,
                        admin_id,
                        attendance_data["model_used"],
                        attendance_data["model_result"],
                        attendance_data.get("expected_result"),
                        attendance_data.get("correct_diagnosis"),
                        attendance_data["image_base64"],
                        attendance_data.get("observations")
                    )
                    

                    if attendance_data["model_used"] == "breast" and bounding_boxes:
                        for box in bounding_boxes:
                            box_query = """
                                INSERT INTO bounding_boxes (
                                    attendance_id, x, y, width, height, confidence, observations
                                )
                                VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """
                            await conn.execute(
                                box_query,
                                returned_id,
                                box["x"],
                                box["y"],
                                box["width"],
                                box["height"],
                                box.get("confidence", 0.0),
                                box.get("observations")
                            )
                    
                    logger.info(f"Attendance added with ID {returned_id}")
                    return {
                        "attendance_id": str(returned_id),
                        "added": True
                    }
        except Exception as e:
            logger.error(f"Error adding attendance: {e}")
            return {
                "attendance_id": "",
                "added": False
            }

    async def get_attendances(self, 
                              admin_id: Optional[str] = None,
                              health_unit_id: Optional[str] = None,
                              professional_id: Optional[str] = None,
                              model_used: Optional[str] = None,
                              limit: int = 100,
                              offset: int = 0) -> List[Dict]:
        """
        Retrieve attendances with optional filtering.
        """
        await self.init_pool()
        try:

            query_parts = ["SELECT * FROM attendances WHERE 1=1"]
            params = []
            param_idx = 1
            
            if admin_id:
                try:
                    admin_uuid = uuid.UUID(admin_id)
                    query_parts.append(f" AND admin_id = ${param_idx}")
                    params.append(admin_uuid)
                    param_idx += 1
                except ValueError:
                    logger.error(f"Invalid UUID format for admin_id: {admin_id}")
            
            if health_unit_id:
                try:
                    unit_uuid = uuid.UUID(health_unit_id)
                    query_parts.append(f" AND health_unit_id = ${param_idx}")
                    params.append(unit_uuid)
                    param_idx += 1
                except ValueError:
                    logger.error(f"Invalid UUID format for health_unit_id: {health_unit_id}")
            
            if professional_id:
                try:
                    prof_uuid = uuid.UUID(professional_id)
                    query_parts.append(f" AND professional_id = ${param_idx}")
                    params.append(prof_uuid)
                    param_idx += 1
                except ValueError:
                    logger.error(f"Invalid UUID format for professional_id: {professional_id}")
            
            if model_used:
                query_parts.append(f" AND model_used = ${param_idx}")
                params.append(model_used)
                param_idx += 1
            

            query_parts.append(f" ORDER BY attendance_date DESC LIMIT ${param_idx} OFFSET ${param_idx+1}")
            params.extend([limit, offset])
            

            query = " ".join(query_parts)
            
            async with self.pool.acquire() as conn:
                attendances = await conn.fetch(query, *params)
                

                result = []
                for attendance in attendances:
                    attendance_dict = {
                        "id": str(attendance["id"]),
                        "professional_id": str(attendance["professional_id"]),
                        "health_unit_id": str(attendance["health_unit_id"]),
                        "admin_id": str(attendance["admin_id"]),
                        "model_used": attendance["model_used"],
                        "model_result": attendance["model_result"],
                        "expected_result": attendance["expected_result"],
                        "correct_diagnosis": attendance["correct_diagnosis"],
                        "image_base64": attendance["image_base64"],
                        "attendance_date": attendance["attendance_date"],
                        "observations": attendance["observations"]
                    }
                    

                    if attendance["model_used"] == "breast":
                        boxes_query = "SELECT * FROM bounding_boxes WHERE attendance_id = $1"
                        boxes = await conn.fetch(boxes_query, attendance["id"])
                        
                        attendance_dict["bounding_boxes"] = [
                            {
                                "id": str(box["id"]),
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"],
                                "height": box["height"],
                                "confidence": box["confidence"],
                                "observations": box["observations"]
                            }
                            for box in boxes
                        ]
                    
                    result.append(attendance_dict)
                
                logger.info(f"Found {len(result)} attendances")
                return result
        except Exception as e:
            logger.error(f"Error fetching attendances: {e}")
            return []
    
    async def get_attendance_by_id(self, attendance_id: str) -> Optional[Dict]:
        """Retrieve an attendance by ID with its bounding boxes if applicable."""
        await self.init_pool()
        try:
            attendance_uuid = uuid.UUID(attendance_id)
            async with self.pool.acquire() as conn:
                query = "SELECT * FROM attendances WHERE id = $1"
                attendance = await conn.fetchrow(query, attendance_uuid)
                
                if not attendance:
                    logger.info(f"Attendance {attendance_id} not found")
                    return None
                
                attendance_dict = {
                    "id": str(attendance["id"]),
                    "professional_id": str(attendance["professional_id"]),
                    "health_unit_id": str(attendance["health_unit_id"]),
                    "admin_id": str(attendance["admin_id"]),
                    "model_used": attendance["model_used"],
                    "model_result": attendance["model_result"],
                    "expected_result": attendance["expected_result"],
                    "correct_diagnosis": attendance["correct_diagnosis"],
                    "image_base64": attendance["image_base64"],
                    "attendance_date": attendance["attendance_date"],
                    "observations": attendance["observations"]
                }
                

                if attendance["model_used"] == "breast":
                    boxes_query = "SELECT * FROM bounding_boxes WHERE attendance_id = $1"
                    boxes = await conn.fetch(boxes_query, attendance_uuid)
                    
                    attendance_dict["bounding_boxes"] = [
                        {
                            "id": str(box["id"]),
                            "x": box["x"],
                            "y": box["y"],
                            "width": box["width"],
                            "height": box["height"],
                            "confidence": box["confidence"],
                            "observations": box["observations"]
                        }
                        for box in boxes
                    ]
                
                logger.info(f"Attendance {attendance_id} found")
                return attendance_dict
        except ValueError:
            logger.error(f"Invalid UUID format: {attendance_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching attendance by ID: {e}")
            return None
    
    async def update_attendance(self, attendance_id: str, attendance_data: Dict) -> Dict:
        """Update attendance information."""
        await self.init_pool()
        try:
            attendance_uuid = uuid.UUID(attendance_id)
            

            professional_id = attendance_data.get("professional_id")
            health_unit_id = attendance_data.get("health_unit_id")
            admin_id = attendance_data.get("admin_id")
            
            if professional_id and isinstance(professional_id, str):
                professional_id = uuid.UUID(professional_id)
            if health_unit_id and isinstance(health_unit_id, str):
                health_unit_id = uuid.UUID(health_unit_id)
            if admin_id and isinstance(admin_id, str):
                admin_id = uuid.UUID(admin_id)
                

            bounding_boxes = attendance_data.pop("bounding_boxes", None)
            
            async with self.pool.acquire() as conn:
                async with conn.transaction():

                    check_query = "SELECT model_used FROM attendances WHERE id = $1"
                    existing = await conn.fetchval(check_query, attendance_uuid)
                    
                    if not existing:
                        logger.info(f"Attendance {attendance_id} not found for update")
                        return {
                            "attendance_id": "",
                            "updated": False
                        }
                    

                    update_parts = []
                    update_params = []
                    param_idx = 1
                    
                    fields = {
                        "professional_id": professional_id,
                        "health_unit_id": health_unit_id,
                        "admin_id": admin_id,
                        "model_result": attendance_data.get("model_result"),
                        "expected_result": attendance_data.get("expected_result"),
                        "correct_diagnosis": attendance_data.get("correct_diagnosis"),
                        "observations": attendance_data.get("observations")
                    }
                    

                    for field, value in fields.items():
                        if value is not None:
                            update_parts.append(f"{field} = ${param_idx}")
                            update_params.append(value)
                            param_idx += 1
                    
                    if update_parts:
                        update_query = f"UPDATE attendances SET {', '.join(update_parts)} WHERE id = ${param_idx} RETURNING id"
                        update_params.append(attendance_uuid)
                        
                        updated_id = await conn.fetchval(update_query, *update_params)
                        

                        if existing == "breast" and bounding_boxes is not None:

                            await conn.execute("DELETE FROM bounding_boxes WHERE attendance_id = $1", attendance_uuid)
                            

                            for box in bounding_boxes:
                                box_query = """
                                    INSERT INTO bounding_boxes (
                                        attendance_id, x, y, width, height, confidence, observations
                                    )
                                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                                """
                                await conn.execute(
                                    box_query,
                                    attendance_uuid,
                                    box["x"],
                                    box["y"],
                                    box["width"],
                                    box["height"],
                                    box.get("confidence", 0.0),
                                    box.get("observations")
                                )
                        
                        logger.info(f"Attendance {attendance_id} updated")
                        return {
                            "attendance_id": attendance_id,
                            "updated": True
                        }
                    else:
                        logger.info(f"No fields to update for attendance {attendance_id}")
                        return {
                            "attendance_id": attendance_id,
                            "updated": False
                        }
        except ValueError:
            logger.error(f"Invalid UUID format: {attendance_id}")
            return {"attendance_id": "", "updated": False}
        except Exception as e:
            logger.error(f"Error updating attendance: {e}")
            return {
                "attendance_id": "",
                "updated": False
            }
    
    async def delete_attendance(self, attendance_id: str) -> Dict:
        """Delete an attendance by ID including associated bounding boxes."""
        await self.init_pool()
        try:
            attendance_uuid = uuid.UUID(attendance_id)
            async with self.pool.acquire() as conn:
                async with conn.transaction():

                    await conn.execute("DELETE FROM bounding_boxes WHERE attendance_id = $1", attendance_uuid)
                    

                    query = "DELETE FROM attendances WHERE id = $1 RETURNING id"
                    deleted_id = await conn.fetchval(query, attendance_uuid)
                    
                    if deleted_id:
                        logger.info(f"Attendance {attendance_id} deleted successfully")
                        return {
                            "attendance_id": attendance_id,
                            "deleted": True
                        }
                    else:
                        logger.info(f"Attendance {attendance_id} not found for deletion")
                        return {
                            "attendance_id": "",
                            "deleted": False
                        }
        except ValueError:
            logger.error(f"Invalid UUID format: {attendance_id}")
            return {"attendance_id": "", "deleted": False}
        except Exception as e:
            logger.error(f"Error deleting attendance: {e}")
            return {
                "attendance_id": "",
                "deleted": False
            }
    
    async def get_statistics(self, admin_id: str, period: str = "month") -> Dict:
        """
        Get statistics about model accuracy and usage.
        period can be 'day', 'week', 'month', 'year'
        """
        await self.init_pool()
        try:
            admin_uuid = uuid.UUID(admin_id)
            

            interval_map = {
                "day": "1 day",
                "week": "1 week",
                "month": "1 month",
                "year": "1 year"
            }
            interval = interval_map.get(period.lower(), "1 month")
            
            async with self.pool.acquire() as conn:

                model_count_query = """
                    SELECT model_used, COUNT(*) as count
                    FROM attendances
                    WHERE admin_id = $1
                    AND attendance_date > CURRENT_DATE - INTERVAL $2
                    GROUP BY model_used
                """
                model_counts = await conn.fetch(model_count_query, admin_uuid, interval)
                

                accuracy_query = """
                    SELECT model_used, 
                           COUNT(*) FILTER (WHERE correct_diagnosis = true) as correct,
                           COUNT(*) as total
                    FROM attendances
                    WHERE admin_id = $1
                    AND attendance_date > CURRENT_DATE - INTERVAL $2
                    AND expected_result IS NOT NULL
                    GROUP BY model_used
                """
                accuracy_data = await conn.fetch(accuracy_query, admin_uuid, interval)
                

                model_usage = {row["model_used"]: row["count"] for row in model_counts}
                model_accuracy = {}
                
                for row in accuracy_data:
                    if row["total"] > 0:
                        accuracy = (row["correct"] / row["total"]) * 100
                        model_accuracy[row["model_used"]] = {
                            "correct": row["correct"],
                            "total": row["total"],
                            "accuracy_percentage": round(accuracy, 2)
                        }
                
                logger.info(f"Statistics retrieved for admin {admin_id}")
                return {
                    "period": period,
                    "model_usage": model_usage,
                    "model_accuracy": model_accuracy
                }
        except ValueError:
            logger.error(f"Invalid UUID format: {admin_id}")
            return {}
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}