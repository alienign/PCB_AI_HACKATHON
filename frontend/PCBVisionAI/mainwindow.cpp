#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QFileDialog>
#include <QPixmap>
#include <QFileInfo>
#include <QMessageBox>
#include <QTimer>
#include <QFrame>
#include <QLabel>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGraphicsDropShadowEffect>
#include <QColor>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

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
        "Images (*.png *.jpg *.jpeg *.bmp)"
        );

    if (filePath.isEmpty()) {
        return;
    }

    selectedImagePath = filePath;

    // После выбора файла переходим на экран загрузки
    ui->stackedWidget->setCurrentWidget(ui->pageLoading);

    ui->progressAnalysis->setValue(0);

    QTimer *timer = new QTimer(this);

    connect(timer, &QTimer::timeout, this, [this, timer]() {
        int value = ui->progressAnalysis->value();

        value += 5;
        ui->progressAnalysis->setValue(value);

        if (value >= 100) {
            timer->stop();
            timer->deleteLater();

            QPixmap pixmap(selectedImagePath);

            ui->labelResultImage->setPixmap(
                pixmap.scaled(
                    ui->labelResultImage->size(),
                    Qt::KeepAspectRatio,
                    Qt::SmoothTransformation
                    )
                );

            ui->labelResultImage->setAlignment(Qt::AlignCenter);

            clearDefectCards();

            addDefectCard("Разрыв дорожки", 0.95);
            addDefectCard("Короткое замыкание", 0.87);
            addDefectCard("Царапина проводника", 0.81);

            ui->labelDefectsTitle->setText("Обнаруженные дефекты  3");

            ui->stackedWidget->setCurrentWidget(ui->pageResult);
        }
    });

    timer->start(100);
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
