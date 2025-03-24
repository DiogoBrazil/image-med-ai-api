from fastapi import APIRouter, Request, Depends, Query
from typing import Optional
from ..controllers.attendace_controller import AttendanceController
from ..interfaces.create_attendance import CreateAttendance
from ..interfaces.update_attendance import UpdateAttendance

# Definir prefixo para as rotas de atendimentos
router = APIRouter(
    prefix="/api/attendances",
    tags=["attendances"],
    responses={404: {"description": "Not found"}},
)

# Instanciar o controller
attendance_controller = AttendanceController()

@router.post("/", status_code=201, summary="Criar um novo atendimento")
async def create_attendance(request: Request, attendance: CreateAttendance):
    """
    Registra um novo atendimento com diagnóstico por IA.
    
    - **Requer perfil de profissional**
    - Registra automaticamente o profissional atual como responsável
    
    Retorna os detalhes do atendimento criado.
    """
    return await attendance_controller.add_attendance(request, attendance)

@router.get("/", summary="Listar atendimentos")
async def get_attendances(
    request: Request, 
    health_unit_id: Optional[str] = None,
    model_used: Optional[str] = Query(None, description="Tipo de modelo utilizado: respiratory, tuberculosis, osteoporosis, breast"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a retornar"),
    offset: int = Query(0, ge=0, description="Número de registros a pular")
):
    """
    Lista atendimentos com filtros opcionais.
    
    - **Administradores**: Veem atendimentos de suas unidades
    - **Profissionais**: Veem apenas seus próprios atendimentos
    
    Parâmetros de filtro:
    - **health_unit_id**: Filtrar por unidade de saúde específica
    - **model_used**: Filtrar por tipo de modelo (respiratory, tuberculosis, osteoporosis, breast)
    - **limit**: Número máximo de registros (padrão: 100)
    - **offset**: Paginação (padrão: 0)
    
    Retorna lista de atendimentos.
    """
    return await attendance_controller.get_attendances(
        request, 
        health_unit_id, 
        model_used,
        limit,
        offset
    )

@router.get("/{attendance_id}", summary="Obter atendimento por ID")
async def get_attendance(
    request: Request, 
    attendance_id: str,
    include_image: bool = Query(False, description="Incluir imagem base64 completa no resultado")
):
    """
    Recupera informações de um atendimento específico.
    
    - **Administradores**: Podem ver atendimentos de suas unidades
    - **Profissionais**: Podem ver apenas seus próprios atendimentos
    
    Parâmetros:
    - **include_image**: Se verdadeiro, inclui a imagem base64 completa na resposta
    
    Retorna detalhes do atendimento solicitado.
    """
    return await attendance_controller.get_attendance_by_id(request, attendance_id, include_image)

@router.put("/{attendance_id}", summary="Atualizar atendimento")
async def update_attendance(request: Request, attendance_id: str, attendance: UpdateAttendance):
    """
    Atualiza informações de um atendimento existente.
    
    - **Administradores**: Podem atualizar atendimentos de suas unidades
    - **Profissionais**: Podem atualizar apenas seus próprios atendimentos
    
    Retorna confirmação da atualização.
    """
    return await attendance_controller.update_attendance(request, attendance_id, attendance)

@router.delete("/{attendance_id}", summary="Remover atendimento")
async def delete_attendance(request: Request, attendance_id: str):
    """
    Remove um atendimento do sistema.
    
    - **Administradores**: Podem remover atendimentos de suas unidades
    - **Profissionais**: Podem remover apenas seus próprios atendimentos
    
    Retorna confirmação da remoção.
    """
    return await attendance_controller.delete_attendance(request, attendance_id)

@router.get("/statistics/summary", summary="Obter estatísticas de atendimentos")
async def get_statistics(
    request: Request,
    period: str = Query("month", regex="^(day|week|month|year)$", description="Período de análise: day, week, month, year")
):
    """
    Obtém estatísticas de uso e precisão dos modelos de IA.
    
    - **Requer perfil de administrador**
    - Fornece estatísticas apenas para as unidades do administrador
    
    Parâmetros:
    - **period**: Período para análise (day, week, month, year)
    
    Retorna estatísticas de uso e precisão dos modelos.
    """
    return await attendance_controller.get_statistics(request, period)