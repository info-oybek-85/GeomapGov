from .start import router as start_router
from .report import router as report_router
from .my_reports import router as my_reports_router
from .guide import router as guide_router
from .staff import router as staff_router


def get_routers():
    # MUHIM: umumiy menyu handlerlari FSM ichidagi generic text
    # handlerlardan oldin turishi kerak. Aks holda foydalanuvchi
    # oldingi jarayonda qolib ketganda “Murojaatlarim” yoki
    # “Qo‘llanma” tugmalari murojaat matni sifatida qabul qilinadi.
    return [start_router, staff_router, my_reports_router, guide_router, report_router]
