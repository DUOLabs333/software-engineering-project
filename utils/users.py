def getUser(user_id):
    with Session(common.database) as session:
        query=select(tables.User).where(tables.User.id==user_id)
        return session.scalars(query).first()