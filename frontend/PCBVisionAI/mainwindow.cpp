#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QFileDialog>
#include <QPixmap>
#include <QFileInfo>
#include <QMessageBox>
#include <QTimer>
#include <QJsonObject>
#include <QFrame>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGraphicsDropShadowEffect>
#include <QColor>
#include <QDebug>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

    apiClient = new ApiClient(this);

    connect(
        apiClient,
        &ApiClient::imageUploaded,
        this,
        [this](qint64 imageId)
        {
            currentImageId = imageId;

            qDebug()
                << "Получен image_id:"
                << currentImageId;

            ui->progressAnalysis->setValue(20);

            apiClient->startAnalysis(
                currentImageId
                );
        }
        );

    connect(apiClient, &ApiClient::uploadFailed, this, [this](const QString &errorMessage) {
        QMessageBox::warning(
            this,
            "Ошибка загрузки",
            errorMessage
            );

        ui->stackedWidget->setCurrentWidget(ui->pageUpload);
    });

    connect(
        apiClient,
        &ApiClient::analysisStarted,
        this,
        [this](qint64 requestId, const QString &status)
        {
            currentRequestId = requestId;

            qDebug()
                << "Получен request_id:"
                << currentRequestId;

            qDebug()
                << "Статус анализа:"
                << status;

            QTimer::singleShot(
                1000,
                this,
                [this]()
                {
                    apiClient->getAnalysisStatus(
                        currentRequestId
                        );
                }
                );
        }
        );

    connect(
        apiClient,
        &ApiClient::analysisStatusReceived,
        this,
        [this](
            qint64 requestId,
            const QString &status,
            const QJsonArray &detections,
            const QString &errorCode,
            const QString &errorMessage
            )
        {
            qDebug()
            << "request_id:"
            << requestId;

            qDebug()
                << "Текущий статус:"
                << status;

            qDebug()
                << "Количество detections:"
                << detections.size();

            if (status == "created" ||
                status == "processing") {

                if (status == "created") {
                    ui->progressAnalysis->setValue(40);
                }

                if (status == "processing") {
                    ui->progressAnalysis->setValue(70);
                }

                QTimer::singleShot(
                    1000,
                    this,
                    [this]()
                    {
                        apiClient->getAnalysisStatus(
                            currentRequestId
                            );
                    }
                    );

                return;
            }

            if (status == "completed") {

                qDebug()
                << "Анализ завершён.";

                ui->progressAnalysis->setValue(100);

                QPixmap pixmap(selectedImagePath);

                ui->labelResultImage->setPixmap(
                    pixmap.scaled(
                        ui->labelResultImage->size(),
                        Qt::KeepAspectRatio,
                        Qt::SmoothTransformation
                        )
                    );

                ui->labelResultImage->setAlignment(
                    Qt::AlignCenter
                    );

                clearBoundingBoxes();
                clearDefectCards();

                if (detections.isEmpty()) {

                    ui->labelDefectsTitle->setText("");
                    ui->labelDefectsCount->setText("");

                    QLabel *emptyLabel =
                        new QLabel(
                            "Дефекты не найдены.",
                            ui->scrollAreaWidgetContents
                            );

                    emptyLabel->setAlignment(
                        Qt::AlignCenter
                        );

                    emptyLabel->setWordWrap(true);

                    emptyLabel->setStyleSheet(
                        "QLabel {"
                        "color: #A9C5BF;"
                        "font-size: 15px;"
                        "padding: 24px;"
                        "border: none;"
                        "}"
                        );

                    verticalLayoutDefects->addWidget(
                        emptyLabel
                        );

                } else {

                    ui->labelDefectsTitle->setText(
                        "Обнаруженные дефекты"
                        );

                    ui->labelDefectsCount->setText(
                        QString::number(
                            detections.size()
                            )
                        );

                    for (int i = 0;
                         i < detections.size();
                         ++i) {

                        QJsonObject detection =
                            detections[i].toObject();

                        QString defectType =
                            detection.value(
                                         "defect_type"
                                         ).toString();

                        double confidence =
                            detection.value(
                                         "confidence"
                                         ).toDouble();

                        QJsonObject bbox =
                            detection.value(
                                         "bbox"
                                         ).toObject();

                        double xMin =
                            bbox.value("x_min")
                                .toDouble();

                        double yMin =
                            bbox.value("y_min")
                                .toDouble();

                        double xMax =
                            bbox.value("x_max")
                                .toDouble();

                        double yMax =
                            bbox.value("y_max")
                                .toDouble();

                        addDefectCard(
                            defectNameRu(defectType),
                            confidence
                            );

                        addBoundingBox(
                            xMin,
                            yMin,
                            xMax,
                            yMax,
                            QString::number(i + 1)
                            );
                    }
                }

                ui->stackedWidget->setCurrentWidget(
                    ui->pageResult
                    );

                return;
            }

            if (status == "failed") {

                qDebug()
                << "Ошибка анализа:"
                << errorCode
                << errorMessage;

                QMessageBox::warning(
                    this,
                    "Ошибка анализа",
                    errorMessage.isEmpty()
                        ? "Не удалось выполнить анализ."
                        : errorMessage
                    );

                return;
            }
        }
        );

    connect(
        apiClient,
        &ApiClient::analysisStatusFailed,
        this,
        [this](const QString &errorMessage)
        {
            qDebug()
            << "Ошибка получения статуса:"
            << errorMessage;

            QMessageBox::warning(
                this,
                "Ошибка соединения",
                errorMessage
                );
        }
        );

    connect(
        apiClient,
        &ApiClient::analysisStartFailed,
        this,
        [this](const QString &errorMessage)
        {
            QMessageBox::warning(
                this,
                "Ошибка запуска анализа",
                errorMessage
                );
        }
        );

    QGraphicsDropShadowEffect *startGlow = new QGraphicsDropShadowEffect(this);
    startGlow->setBlurRadius(24);
    startGlow->setOffset(0, 0);
    startGlow->setColor(QColor(43, 240, 200, 140));
    ui->btnStart->setGraphicsEffect(startGlow);

    verticalLayoutDefects = new QVBoxLayout(ui->scrollAreaWidgetContents);

    verticalLayoutDefects->setContentsMargins(8, 8, 8, 8);
    verticalLayoutDefects->setSpacing(10);
    verticalLayoutDefects->setAlignment(Qt::AlignTop);

    ui->stackedWidget->setCurrentWidget(ui->pageStart);

    connect(ui->btnChooseFile,
            &QPushButton::clicked,
            this,
            &MainWindow::chooseImage);

    connect(ui->btnStart, &QPushButton::clicked, this, [this]() {
        ui->stackedWidget->setCurrentWidget(ui->pageUpload);
    });

    connect(ui->btnBackUpload, &QPushButton::clicked, this, [this]() {
        ui->stackedWidget->setCurrentWidget(ui->pageStart);
    });

    connect(ui->btnBackResult, &QPushButton::clicked, this, [this]() {
        ui->stackedWidget->setCurrentWidget(ui->pageUpload);
    });
}

MainWindow::~MainWindow()
{
    delete ui;
}

void MainWindow::chooseImage()
{
    QString filePath = QFileDialog::getOpenFileName(
        this,
        "Выберите изображение платы",
        "",
        "Images (*.png *.jpg *.jpeg)"
        );

    if (filePath.isEmpty()) {
        return;
    }

    selectedImagePath = filePath;

    ui->stackedWidget->setCurrentWidget(ui->pageLoading);

    ui->progressAnalysis->setValue(0);

    apiClient->uploadImage(selectedImagePath);
}

void MainWindow::addDefectCard(const QString &name, double confidence)
{
    QFrame *card = new QFrame(ui->scrollAreaWidgetContents);

    card->setStyleSheet(
        "QFrame {"
        "background-color: #0E2A26;"
        "border: 1px solid #1C443E;"
        "border-radius: 12px;"
        "}"
        );

    QVBoxLayout *cardLayout = new QVBoxLayout(card);

    cardLayout->setContentsMargins(14, 12, 14, 12);
    cardLayout->setSpacing(6);

    QLabel *nameLabel = new QLabel(name, card);
    nameLabel->setStyleSheet(
        "QLabel {"
        "color: #EAF7F4;"
        "font-size: 14px;"
        "font-weight: 600;"
        "border: none;"
        "}"
        );

    QLabel *confidenceLabel = new QLabel(card);

    nameLabel->setWordWrap(true);

    int percent = static_cast<int>(confidence * 100.0);

    confidenceLabel->setText(
        QString("Уверенность: %1%").arg(percent)
        );

    confidenceLabel->setStyleSheet(
        "QLabel {"
        "color: #20D6A3;"
        "font-size: 16px;"
        "font-weight: 700;"
        "border: none;"
        "}"
        );

    cardLayout->addWidget(nameLabel);
    cardLayout->addWidget(confidenceLabel);

    verticalLayoutDefects->addWidget(card);
}

void MainWindow::clearDefectCards()
{
    QLayoutItem *item;

    while ((item = verticalLayoutDefects->takeAt(0)) != nullptr) {

        if (item->widget()) {
            delete item->widget();
        }

        delete item;
    }
}


void MainWindow::addBoundingBox(double xMin,
                                double yMin,
                                double xMax,
                                double yMax,
                                const QString &text)
{
    QPixmap originalPixmap(selectedImagePath);

    if (originalPixmap.isNull()) {
        return;
    }

    int labelWidth = ui->labelResultImage->width();
    int labelHeight = ui->labelResultImage->height();

    double scaleX =
        static_cast<double>(labelWidth) /
        originalPixmap.width();

    double scaleY =
        static_cast<double>(labelHeight) /
        originalPixmap.height();

    double scale = qMin(scaleX, scaleY);

    int imageWidth =
        static_cast<int>(originalPixmap.width() * scale);

    int imageHeight =
        static_cast<int>(originalPixmap.height() * scale);

    int offsetX =
        (labelWidth - imageWidth) / 2;

    int offsetY =
        (labelHeight - imageHeight) / 2;

    int x =
        offsetX +
        static_cast<int>(xMin * imageWidth);

    int y =
        offsetY +
        static_cast<int>(yMin * imageHeight);

    int width =
        static_cast<int>((xMax - xMin) * imageWidth);

    int height =
        static_cast<int>((yMax - yMin) * imageHeight);

    QFrame *bbox =
        new QFrame(ui->labelResultImage);

    bbox->setObjectName("bboxFrame");

    bbox->setGeometry(
        x,
        y,
        width,
        height
        );

    bbox->setStyleSheet(
        "QFrame#bboxFrame {"
        "background-color: transparent;"
        "border: 3px solid #FF4D4D;"
        "border-radius: 4px;"
        "}"
        );

    QLabel *bboxLabel =
        new QLabel(text, bbox);

    bboxLabel->setStyleSheet(
        "QLabel {"
        "background-color: #FF4D4D;"
        "color: white;"
        "font-weight: 700;"
        "font-size: 12px;"
        "padding: 2px 5px;"
        "border-radius: 3px;"
        "}"
        );

    bboxLabel->adjustSize();
    bboxLabel->move(4, 4);

    bbox->show();
    bbox->raise();
}

void MainWindow::clearBoundingBoxes()
{
    QList<QFrame *> boxes =
        ui->labelResultImage
            ->findChildren<QFrame *>("bboxFrame");

    for (QFrame *box : boxes) {
        delete box;
    }
}

QString MainWindow::defectNameRu(const QString &defectType)
{
    if (defectType == "short")
        return "Короткое замыкание";

    if (defectType == "open")
        return "Разрыв дорожки";

    if (defectType == "conductor_scratch")
        return "Царапина проводника";

    if (defectType == "spur")
        return "Отросток проводника";

    if (defectType == "spurious_copper")
        return "Лишняя медь";

    if (defectType == "mouse_bite")
        return "Дефект типа Mouse Bite";

    if (defectType == "hole_breakout")
        return "Повреждение отверстия";

    if (defectType == "conductor_foreign_object")
        return "Посторонний объект на проводнике";

    if (defectType == "base_material_foreign_object")
        return "Посторонний объект на основании";

    return defectType;
}
