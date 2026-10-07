#include "mainwindow.h"
#include "ui_mainwindow.h"

#include <QFileDialog>
#include <QPixmap>
#include <QFileInfo>
#include <QMessageBox>
#include <QTimer>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);

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

            ui->stackedWidget->setCurrentWidget(ui->pageResult);
        }
    });

    timer->start(100);
}
