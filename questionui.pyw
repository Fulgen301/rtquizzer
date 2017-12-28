#!/usr/bin/env python3
import sys
import pickle
import threading
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
            self.questions = pickle.load(fobj)
        
        for category in self.questions.copy():
            if ":" in category:
                q = self.questions[category][0]
                del self.questions[category]
                category, question = category.split(":", 1)
                q[0] = f"{question}{q[0]}"
                if category in self.questions:
                    self.questions[category].append(q)
                else:
                    self.questions[category] = [q]
        
        for category in self.questions:
            entry_cat = QTreeWidgetItem(self.treeQuestions)
            entry_cat.setText(0, category.strip())
            for q in self.questions[category]:
                entry_q = QTreeWidgetItem(entry_cat)
                entry_q.setText(0, q[0])
                setattr(entry_q, "question", q)
        
        del self.questions
        
        self.treeQuestions.sortItems(0, 0)
    
    def treeItemChanged(self, current : QTreeWidgetItem, previous : QTreeWidgetItem):
        [i.clear() for i in [self.lblCategory, self.txtQuestion, self.txtAnswer]]
        if not (current and current.parent()):
            [i.setEnabled(False) for i in [self.lblCategory, self.txtQuestion, self.txtAnswer, self.btnUpdate]]
            return
        
        [i.setEnabled(True) for i in [self.lblCategory, self.txtQuestion, self.txtAnswer, self.btnUpdate]]
        self.lblCategory.setText(current.parent().text(0))
        self.txtQuestion.setPlainText(current.question[0])
        self.txtAnswer.setText(current.question[2])
    
    def updateEntry(self):
        current = self.treeQuestions.currentItem()
        if not (current and current.parent()):
            return
        
        current.question[0] = self.txtQuestion.toPlainText()
        current.setText(0, self.txtQuestion.toPlainText())
        current.question[2] = self.txtAnswer.text()
    
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
        if current.parent():
            current = current.parent()
        
        new = QTreeWidgetItem(current)
        new.setText(0, "Neuer Eintrag")
        setattr(new, "question", ["", "", "", 0])
        self.treeQuestions.setCurrentItem(new)
    
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
        q = {}
        for i in range(self.treeQuestions.topLevelItemCount()):
            cat = self.treeQuestions.topLevelItem(i)
            q[cat.text(0)] = []
            for j in range(cat.childCount()):
                item = cat.child(j)
                q[cat.text(0)].append([item.question[0], "", item.question[2], 0])
        
        with open("questions.pickle", "wb") as fobj:
            pickle.dump(q, fobj)
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    q = QuestionUI()
    q.show()
    sys.exit(app.exec())
