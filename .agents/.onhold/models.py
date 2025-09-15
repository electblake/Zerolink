class LinkDir(Base):
    __tablename__ = "link_dirs"

    link_inode: Mapped[int] = mapped_column(Integer, primary_key=True)
    recent_name: Mapped[str] = mapped_column(String, nullable=False)
    parent_dir: Mapped[str | None] = mapped_column(String, nullable=True)

    rules: Mapped[list["Rule"]] = relationship(
        back_populates="link",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    link_inode: Mapped[int] = mapped_column(
        ForeignKey("link_dirs.link_inode", ondelete="CASCADE"), nullable=False
    )
    target_inode: Mapped[int] = mapped_column(Integer, nullable=False)
    target_name: Mapped[str] = mapped_column(String, nullable=False)
    target_path: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("link_inode", "target_inode", name="uq_rule_pair"),
    )

    link: Mapped[LinkDir] = relationship(back_populates="rules")
