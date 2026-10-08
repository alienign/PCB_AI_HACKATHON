#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>
#include <QString>
#include <QVBoxLayout>

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void chooseImage();

private:
    void addDefectCard(const QString &name, double confidence);
    void clearDefectCards();
    QVBoxLayout *verticalLayoutDefects;

    Ui::MainWindow *ui;

    QString selectedImagePath;
};

#endif // MAINWINDOW_H
