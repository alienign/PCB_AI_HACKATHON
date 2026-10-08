#include "apiclient.h"

#include <QFile>
#include <QFileInfo>
#include <QHttpMultiPart>
#include <QHttpPart>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>
#include <QJsonArray>
#include <QDebug>

ApiClient::ApiClient(QObject *parent)
    : QObject(parent)
{
    networkManager = new QNetworkAccessManager(this);
}

void ApiClient::uploadImage(const QString &filePath)
{
    QFileInfo fileInfo(filePath);

    QFile *file = new QFile(filePath);

    if (!file->open(QIODevice::ReadOnly)) {
        emit uploadFailed("Не удалось открыть выбранный файл.");
        file->deleteLater();
        return;
    }

    QHttpMultiPart *multiPart =
        new QHttpMultiPart(QHttpMultiPart::FormDataType);

    QHttpPart filePart;

    QString disposition =
        QString("form-data; name=\"file\"; filename=\"%1\"")
            .arg(fileInfo.fileName());

    filePart.setHeader(
        QNetworkRequest::ContentDispositionHeader,
        disposition
        );

    QString suffix = fileInfo.suffix().toLower();

    QString contentType;

    if (suffix == "png") {
        contentType = "image/png";
    } else {
        contentType = "image/jpeg";
    }

    filePart.setHeader(
        QNetworkRequest::ContentTypeHeader,
        contentType
        );

    file->setParent(multiPart);
    filePart.setBodyDevice(file);

    multiPart->append(filePart);

    QNetworkRequest request(
        QUrl(baseUrl + "/images")
        );

    request.setRawHeader(
        "ngrok-skip-browser-warning",
        "true"
        );

    QNetworkReply *reply =
        networkManager->post(request, multiPart);

    multiPart->setParent(reply);

    connect(
        reply,
        &QNetworkReply::finished,
        this,
        [this, reply]()
        {
            QByteArray responseData = reply->readAll();

            if (reply->error() != QNetworkReply::NoError) {

                QString errorMessage =
                    QString::fromUtf8(responseData);

                if (errorMessage.isEmpty()) {
                    errorMessage = reply->errorString();
                }

                emit uploadFailed(errorMessage);

                reply->deleteLater();
                return;
            }

            QJsonParseError parseError;

            QJsonDocument document =
                QJsonDocument::fromJson(
                    responseData,
                    &parseError
                    );

            if (parseError.error != QJsonParseError::NoError ||
                !document.isObject()) {

                emit uploadFailed(
                    "Backend вернул некорректный ответ."
                    );

                reply->deleteLater();
                return;
            }

            QJsonObject object = document.object();

            if (!object.contains("image_id")) {

                emit uploadFailed(
                    "В ответе backend отсутствует image_id."
                    );

                reply->deleteLater();
                return;
            }

            qint64 imageId =
                object.value("image_id")
                    .toVariant()
                    .toLongLong();

            emit imageUploaded(imageId);

            reply->deleteLater();
        }
        );
}

void ApiClient::startAnalysis(qint64 imageId)
{
    QNetworkRequest request(
        QUrl(baseUrl + "/analysis-requests")
        );

    request.setRawHeader(
        "ngrok-skip-browser-warning",
        "true"
        );

    request.setHeader(
        QNetworkRequest::ContentTypeHeader,
        "application/json"
        );

    QJsonObject jsonObject;

    jsonObject["image_id"] = imageId;

    QJsonDocument jsonDocument(jsonObject);

    QByteArray requestData =
        jsonDocument.toJson(QJsonDocument::Compact);

    QNetworkReply *reply =
        networkManager->post(
            request,
            requestData
            );

    connect(
        reply,
        &QNetworkReply::finished,
        this,
        [this, reply]()
        {
            QByteArray responseData =
                reply->readAll();

            if (reply->error() != QNetworkReply::NoError) {

                QString errorMessage =
                    QString::fromUtf8(responseData);

                if (errorMessage.isEmpty()) {
                    errorMessage =
                        reply->errorString();
                }

                emit analysisStartFailed(
                    errorMessage
                    );

                reply->deleteLater();
                return;
            }

            QJsonParseError parseError;

            QJsonDocument document =
                QJsonDocument::fromJson(
                    responseData,
                    &parseError
                    );

            if (parseError.error != QJsonParseError::NoError ||
                !document.isObject()) {

                emit analysisStartFailed(
                    "Backend вернул некорректный ответ при запуске анализа."
                    );

                reply->deleteLater();
                return;
            }

            QJsonObject object =
                document.object();

            if (!object.contains("request_id") ||
                !object.contains("status")) {

                emit analysisStartFailed(
                    "В ответе backend отсутствует request_id или status."
                    );

                reply->deleteLater();
                return;
            }

            qint64 requestId =
                object.value("request_id")
                    .toVariant()
                    .toLongLong();

            QString status =
                object.value("status")
                    .toString();

            emit analysisStarted(
                requestId,
                status
                );

            reply->deleteLater();
        }
        );
}

void ApiClient::getAnalysisStatus(qint64 requestId)
{
    QNetworkRequest request(
        QUrl(
            baseUrl
            + "/analysis-requests/"
            + QString::number(requestId)
            )
        );

    request.setRawHeader(
        "ngrok-skip-browser-warning",
        "true"
        );

    QNetworkReply *reply =
        networkManager->get(request);

    connect(
        reply,
        &QNetworkReply::finished,
        this,
        [this, reply, requestId]()
        {
            QByteArray responseData =
                reply->readAll();

            qDebug() << "GET status HTTP:"
                     << reply->attribute(
                                 QNetworkRequest::HttpStatusCodeAttribute
                                 ).toInt();

            qDebug() << "GET status RAW:"
                     << QString::fromUtf8(responseData);

            if (reply->error() != QNetworkReply::NoError) {

                QString errorMessage =
                    QString::fromUtf8(responseData);

                if (errorMessage.isEmpty()) {
                    errorMessage =
                        reply->errorString();
                }

                emit analysisStatusFailed(
                    errorMessage
                    );

                reply->deleteLater();
                return;
            }

            QJsonParseError parseError;

            QJsonDocument document =
                QJsonDocument::fromJson(
                    responseData,
                    &parseError
                    );

            if (parseError.error !=
                    QJsonParseError::NoError ||
                !document.isObject()) {

                emit analysisStatusFailed(
                    "Backend вернул некорректный ответ статуса анализа."
                    );

                reply->deleteLater();
                return;
            }

            QJsonObject object =
                document.object();

            QString status =
                object.value("status").toString();

            QJsonArray detections =
                object.value("detections").toArray();

            QString errorCode =
                object.value("error_code").toString();

            QString errorMessage =
                object.value("error_message").toString();

            emit analysisStatusReceived(
                requestId,
                status,
                detections,
                errorCode,
                errorMessage
                );

            reply->deleteLater();
        }
        );
}

void ApiClient::getHistory()
{
    QNetworkRequest request(
        QUrl(
            baseUrl +
            "/analysis-requests?limit=20&offset=0"
            )
        );

    request.setRawHeader(
        "ngrok-skip-browser-warning",
        "true"
        );

    QNetworkReply *reply =
        networkManager->get(request);

    connect(
        reply,
        &QNetworkReply::finished,
        this,
        [this, reply]()
        {
            QByteArray responseData =
                reply->readAll();

            qDebug()
                << "HISTORY HTTP:"
                << reply->attribute(
                            QNetworkRequest::HttpStatusCodeAttribute
                            ).toInt();

            qDebug()
                << "HISTORY RAW:"
                << QString::fromUtf8(responseData);

            if (reply->error() !=
                QNetworkReply::NoError) {

                emit historyFailed(
                    reply->errorString()
                    );

                reply->deleteLater();
                return;
            }

            QJsonDocument document =
                QJsonDocument::fromJson(
                    responseData
                    );

            /*
             * Пока намеренно не предполагаем
             * точную структуру history-response.
             */
            if (document.isArray()) {

                emit historyReceived(
                    document.array()
                    );

            } else {

                emit historyFailed(
                    "Неизвестный формат истории."
                    );
            }

            reply->deleteLater();
        }
        );
}

void ApiClient::getImage(qint64 imageId)
{
    QUrl url(
        baseUrl +
        "/images/" +
        QString::number(imageId)
        );

    QNetworkRequest request(url);

    request.setRawHeader(
        "ngrok-skip-browser-warning",
        "true"
        );

    QNetworkReply *reply =
        networkManager->get(request);

    connect(
        reply,
        &QNetworkReply::finished,
        this,
        [this, reply, imageId]()
        {
            int statusCode =
                reply->attribute(
                         QNetworkRequest::HttpStatusCodeAttribute
                         ).toInt();

            QByteArray data =
                reply->readAll();

            qDebug()
                << "GET IMAGE HTTP:"
                << statusCode
                << "imageId:"
                << imageId
                << "bytes:"
                << data.size();

            if (statusCode >= 200 &&
                statusCode < 300) {

                QString contentType =
                    reply->header(
                             QNetworkRequest::ContentTypeHeader
                             ).toString();

                emit imageReceived(
                    imageId,
                    data,
                    contentType
                    );

            } else {

                QString errorMessage;

                if (statusCode == 404) {
                    errorMessage =
                        "Исходное изображение анализа не найдено.";
                } else {
                    errorMessage =
                        QString(
                            "Не удалось загрузить изображение. HTTP %1"
                            ).arg(statusCode);
                }

                emit imageReceiveFailed(
                    imageId,
                    errorMessage
                    );
            }

            reply->deleteLater();
        }
        );
}
