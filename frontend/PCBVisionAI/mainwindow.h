#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include "apiclient.h"

#include <QMainWindow>
#include <QString>
#include <QVBoxLayout>


QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

struct Detection
{
    QString defectType;
    double confidence;

    double xMin;
    double yMin;
    double xMax;
    double yMax;
};

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

    void addBoundingBox(double xMin,
                        double yMin,
                        double xMax,
                        double yMax,
                        const QString &text);

    void clearBoundingBoxes();

    QString defectNameRu(const QString &defectType);

    QVBoxLayout *verticalLayoutDefects;

    ApiClient *apiClient;
    qint64 currentImageId = -1;

    qint64 currentRequestId = -1;

    Ui::MainWindow *ui;

    QString selectedImagePath;
};

#endif // MAINWINDOW_H
