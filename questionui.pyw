#!/usr/bin/env python3
import sys
import pickle
import threading
import collections
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import *

class QuestionUI(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("questions.ui", self)
        
        header = QTreeWidgetItem()
        header.setText(0, self.tr("Fragen"))
        self.treeQuestions.setHeaderItem(header)
        self.treeQuestions.currentItemChanged.connect(self.treeItemChanged)
        self.treeQuestions.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeQuestions.customContextMenuRequested.connect(self.showContextMenu)
        self.btnUpdate.clicked.connect(self.updateEntry)
        self.actSave.triggered.connect(self.save)
        
        with open("questions.pickle", "rb") as fobj:
            questions = pickle.load(fobj)
        
        new = collections.defaultdict(lambda: list())
        
        for q in questions:
            if ":" in q[0]:
                q[0], que = q[0].split(":", 1)
                q[1] = f"{que}{q[1]}"
            
            new[q[0].strip()].append(q[1:])
        
        for category in new:
            entry_cat = QTreeWidgetItem(self.treeQuestions)
            entry_cat.setText(0, category.strip())
            for q in new[category]:
                entry_q = QTreeWidgetItem(entry_cat)
                entry_q.setText(0, q[0])
                setattr(entry_q, "question", q)
        
        del questions, new
        
        self.treeQuestions.sortItems(0, 0)
    
    def treeItemChanged(self, current : QTreeWidgetItem, previous : QTreeWidgetItem):
        [i.clear() for i in [self.lblCategory, self.txtQuestion, self.txtAnswer]]
        self.treeQuestions.sortItems(0, 0)
        if not (current and current.parent()):
            [i.setEnabled(False) for i in [self.lblCategory, self.txtQuestion, self.txtAnswer, self.btnUpdate]]
            return
        
        [i.setEnabled(True) for i in [self.lblCategory, self.txtQuestion, self.txtAnswer, self.btnUpdate]]
        self.lblCategory.setText(current.parent().text(0))
        self.txtQuestion.setPlainText(current.question[0])
        self.txtAnswer.setText(current.question[1])
    
    def updateEntry(self):
        current = self.treeQuestions.currentItem()
        if not (current and current.parent()):
            return
        
        current.question[0] = self.txtQuestion.toPlainText()
        current.setText(0, self.txtQuestion.toPlainText())
        current.question[1] = self.txtAnswer.text()
    
    def deleteEntry(self):
        current = self.treeQuestions.currentItem()
        if current.parent():
            current.parent().removeChild(current)
        else:
            self.treeQuestions.takeTopLevelItem(self.treeQuestions.indexOfTopLevelItem(current))
    
    def addEntry(self):
        current = self.treeQuestions.currentItem()
        if not current:
            return
        if not current.parent():
            current = self.addCategory()
        else:
            current = current.parent()
        new = QTreeWidgetItem(current)
        new.setText(0, "Neuer Eintrag")
        setattr(new, "question", ["", "", "", 0])
        self.treeQuestions.setCurrentItem(new)
    
    def addCategory(self):
        new = QTreeWidgetItem(self.treeQuestions)
        new.setText(0, QInputDialog.getText(self, "Neuer Eintrag", "Name der Kategorie:")[0])
        return new
    
    def showContextMenu(self, pos):
        item = self.treeQuestions.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        actAdd = QAction(QIcon.fromTheme("list-add"), "Eintrag hinzufügen")
        actAdd.triggered.connect(self.addEntry)
        menu.addAction(actAdd)
        
        actDelete = QAction(QIcon.fromTheme("list-remove"), "Löschen")
        actDelete.triggered.connect(self.deleteEntry)
        menu.addAction(actDelete)
        
        menu.exec(self.treeQuestions.mapToGlobal(pos))
    
    def save(self):
        q = []
        for i in range(self.treeQuestions.topLevelItemCount()):
            cat = self.treeQuestions.topLevelItem(i)
            for j in range(cat.childCount()):
                item = cat.child(j)
                q.append([cat.text(0), *(item.question)])
        
        with open("questions.pickle", "wb") as fobj:
            pickle.dump(q, fobj)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    q = QuestionUI()
    q.show()
    sys.exit(app.exec())
