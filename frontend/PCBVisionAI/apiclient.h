#ifndef APICLIENT_H
#define APICLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QString>
#include <QJsonArray>
#include <QByteArray>

class ApiClient : public QObject
{
    Q_OBJECT

public:
    explicit ApiClient(QObject *parent = nullptr);

    void uploadImage(const QString &filePath);

    void startAnalysis(qint64 imageId);
    void getAnalysisStatus(qint64 requestId);
    void getImage(qint64 imageId);

    void getHistory();

signals:
    void imageUploaded(qint64 imageId);
    void uploadFailed(const QString &errorMessage);

    void analysisStarted(qint64 requestId, const QString &status);
    void analysisStartFailed(const QString &errorMessage);

    void historyReceived(const QJsonArray &history);
    void historyFailed(const QString &errorMessage);

    void analysisStatusReceived(
        qint64 requestId,
        const QString &status,
        const QJsonArray &detections,
        const QString &errorCode,
        const QString &errorMessage
        );

    void analysisStatusFailed(const QString &errorMessage);

    void imageReceived(
        qint64 imageId,
        const QByteArray &imageData,
        const QString &contentType
        );

    void imageReceiveFailed(
        qint64 imageId,
        const QString &errorMessage
        );

private:
    QNetworkAccessManager *networkManager;

    QString baseUrl = "https://gumming-unmasking-unhitched.ngrok-free.dev";
};

#endif // APICLIENT_H
