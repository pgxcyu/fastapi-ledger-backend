from app.core.exceptions import BizException
from app.db.models import Transaction
import pandas as pd

def export_transactions_by_user_func(db, user_id: str):
    # 导出excel文件
    try:
        # 查询用户交易记录
        rows = db.query(Transaction).filter(Transaction.create_userid == user_id).all()
        if not rows:
            raise BizException(code=500, message="该用户暂无交易记录")

        # 清洗模型 -> dict（去掉 SQLAlchemy 内部字段）
        def to_row(t):
            d = {k: v for k, v in t.__dict__.items() if not k.startswith("_sa_")}
            # 可选：把 datetime 转成字符串，避免部分引擎写入时出问题
            for k, v in list(d.items()):
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            return d

        df = pd.DataFrame([to_row(t) for t in rows])

        # 建议把文件落到静态目录，便于前端下载
        import os
        export_dir = os.path.join("static", "exports", str(user_id))
        os.makedirs(export_dir, exist_ok=True)
        out_path = os.path.join(export_dir, "transactions.xlsx")
        df.to_excel(out_path, index=False)  # 需要安装 openpyxl

        # 返回“可下载”的 URL（而不是相对工作目录的文件名）
        download_url = f"/static/exports/{user_id}/transactions.xlsx"
        return {"path": out_path, "url": download_url}
    except Exception as e:
        raise BizException(code=500, message=str(e))