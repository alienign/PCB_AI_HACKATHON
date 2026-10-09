#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include "apiclient.h"

#include <QMainWindow>
#include <QString>
#include <QVBoxLayout>
#include <QList>
#include <QResizeEvent>
#include <QJsonArray>

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

    int number = 0;
    bool selected = true;
};

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void chooseImage();

protected:
    void resizeEvent(QResizeEvent *event) override;

private:
    void addDefectCard(
        int number,
        const QString &name,
        double confidence
        );
    void clearDefectCards();

    void addBoundingBox(double xMin,
                        double yMin,
                        double xMax,
                        double yMax,
                        const QString &text);

    void clearBoundingBoxes();

    void updateResultImage();
    void redrawBoundingBoxes();

    bool openingHistoryItem = false;

    qint64 historyRequestId = -1;
    qint64 historyImageId = -1;
    QJsonArray historyDetections;

    bool showBoundingBoxes = true;

    QString defectNameRu(const QString &defectType);

    QVBoxLayout *verticalLayoutDefects;
    QVBoxLayout *verticalLayoutHistory = nullptr;

    void clearHistoryCards();
    void addHistoryCard(
        qint64 requestId,
        qint64 imageId,
        const QString &status,
        const QString &createdAt,
        int detectionsCount
        );

    ApiClient *apiClient;
    qint64 currentImageId = -1;

    qint64 currentRequestId = -1;

    double currentZoom = 1.0;

    QList<Detection> currentDetections;

    Ui::MainWindow *ui;

    QString selectedImagePath;
};

#endif // MAINWINDOW_H
